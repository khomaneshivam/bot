import os
import re
import json
import time
import sqlite3
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

try:
    import pymysql
    import pymysql.cursors
    PYMYSQL_AVAILABLE = True
except ImportError:
    PYMYSQL_AVAILABLE = False

DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
DEFAULT_SQLITE_PATH = os.path.join(DB_DIR, "quant_trade_ledger.db")

class RowDict(dict):
    """Dictionary supporting integer indexing for SQL column compatibility."""
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)

if PYMYSQL_AVAILABLE:
    class RowCursor(pymysql.cursors.DictCursor):
        def _conv_row(self, row):
            res = super()._conv_row(row)
            return RowDict(res) if res is not None else None
else:
    RowCursor = None

class MySQLCursorWrapper:
    """Wraps PyMySQL cursor to normalize queries and parameter placeholders."""
    def __init__(self, raw_cursor):
        self._cursor = raw_cursor

    def execute(self, sql: str, params=None):
        clean_sql = sql.strip()
        # No-op for SQLite PRAGMA statements
        if clean_sql.upper().startswith("PRAGMA"):
            return self

        # Normalize INSERT OR REPLACE INTO for MySQL
        clean_sql = re.sub(r"INSERT\s+OR\s+REPLACE\s+INTO", "REPLACE INTO", clean_sql, flags=re.IGNORECASE)

        # Replace ? placeholders with %s
        clean_sql = clean_sql.replace("?", "%s")

        if params is not None:
            self._cursor.execute(clean_sql, params)
        else:
            self._cursor.execute(clean_sql)
        return self

    def executemany(self, sql: str, seq_of_parameters):
        clean_sql = sql.strip()
        clean_sql = re.sub(r"INSERT\s+OR\s+REPLACE\s+INTO", "REPLACE INTO", clean_sql, flags=re.IGNORECASE)
        clean_sql = clean_sql.replace("?", "%s")
        return self._cursor.executemany(clean_sql, seq_of_parameters)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def fetchmany(self, size=None):
        return self._cursor.fetchmany(size) if size else self._cursor.fetchmany()

    def close(self):
        self._cursor.close()

    def __iter__(self):
        return iter(self._cursor)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    @property
    def description(self):
        return self._cursor.description


class MySQLConnectionWrapper:
    """Wraps PyMySQL connection to mirror SQLite connection API."""
    def __init__(self, raw_conn):
        self._conn = raw_conn
        self.row_factory = None

    def cursor(self, cursorclass=None):
        cur_class = cursorclass or RowCursor
        return MySQLCursorWrapper(self._conn.cursor(cur_class))

    def execute(self, sql: str, params=None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()


class Database:
    """
    Unified Storage Layer for QuantAI Platform supporting MySQL & SQLite.
    Automatically provisions tables, manages connections, and ensures cross-database compatibility.
    """
    def __init__(
        self,
        db_path: Optional[str] = None,
        backend: Optional[str] = None,
        mysql_host: Optional[str] = None,
        mysql_port: Optional[int] = None,
        mysql_user: Optional[str] = None,
        mysql_password: Optional[str] = None,
        mysql_db: Optional[str] = None
    ):
        os.makedirs(DB_DIR, exist_ok=True)
        self.db_path = db_path or os.getenv("SQLITE_DB_PATH", DEFAULT_SQLITE_PATH)

        # Detect or configure backend
        env_backend = os.getenv("DB_BACKEND", "").lower().strip()
        if backend:
            self.backend = backend.lower().strip()
        elif env_backend in ("mysql", "sqlite"):
            self.backend = env_backend
        elif os.getenv("DB_HOST") or os.getenv("DB_USER") or os.getenv("DB_PASSWORD"):
            self.backend = "mysql"
        else:
            self.backend = "mysql"  # Default to MySQL

        self.mysql_host = mysql_host or os.getenv("DB_HOST", "localhost")
        self.mysql_port = int(mysql_port or os.getenv("DB_PORT", "3306"))
        self.mysql_user = mysql_user or os.getenv("DB_USER", "root")
        self.mysql_password = mysql_password or os.getenv("DB_PASSWORD", "@Shivam930738")
        self.mysql_db = mysql_db or os.getenv("DB_NAME", "trading_bot_db")

        # Fallback check if pymysql is missing
        if self.backend == "mysql" and not PYMYSQL_AVAILABLE:
            print("[Database] [WARN] PyMySQL not installed. Falling back to SQLite backend.")
            self.backend = "sqlite"

        # Initialize schema
        self._init_database()

    def initialize_db(self):
        """Explicit entry point for server startup sequence."""
        self._init_database()

    def get_connection(self):
        """Returns active database connection with normalized interface."""
        if self.backend == "mysql":
            try:
                raw_conn = pymysql.connect(
                    host=self.mysql_host,
                    port=self.mysql_port,
                    user=self.mysql_user,
                    password=self.mysql_password,
                    database=self.mysql_db,
                    charset="utf8mb4",
                    autocommit=False
                )
                return MySQLConnectionWrapper(raw_conn)
            except Exception as e:
                # If MySQL is configured but temporarily unavailable, warn and return SQLite fallback
                print(f"[Database] [WARN] MySQL connection error ({e}). Using SQLite fallback.")
                return self._get_sqlite_connection()
        else:
            return self._get_sqlite_connection()

    def _get_sqlite_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.db_path,
            timeout=10.0,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        return conn

    def _init_database(self):
        """Initializes tables, indexes, and schema definitions idempotently."""
        if self.backend == "mysql":
            self._init_mysql_database()
        else:
            self._init_sqlite_database()

    def _init_mysql_database(self):
        try:
            # First ensure database exists
            init_conn = pymysql.connect(
                host=self.mysql_host,
                port=self.mysql_port,
                user=self.mysql_user,
                password=self.mysql_password,
                charset="utf8mb4"
            )
            with init_conn.cursor() as cur:
                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{self.mysql_db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            init_conn.close()

            # Connect to database and create tables
            conn = self.get_connection()
            cursor = conn.cursor()

            # 1. Users Table for RBAC
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id VARCHAR(64) PRIMARY KEY,
                    username VARCHAR(64) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(32) NOT NULL,
                    is_active INT DEFAULT 1,
                    created_at VARCHAR(32) NOT NULL,
                    last_login VARCHAR(32)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            # 2. Authenticated Active Sessions & Tokens
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS active_sessions (
                    token_hash VARCHAR(64) PRIMARY KEY,
                    user_id VARCHAR(64) NOT NULL,
                    role VARCHAR(32) NOT NULL,
                    created_at VARCHAR(32) NOT NULL,
                    expires_at VARCHAR(32) NOT NULL,
                    is_revoked INT DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            # 3. Orders Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id VARCHAR(64) PRIMARY KEY,
                    client_order_id VARCHAR(64) UNIQUE NOT NULL,
                    broker_order_id VARCHAR(64),
                    symbol VARCHAR(32) NOT NULL,
                    side VARCHAR(16) NOT NULL,
                    order_type VARCHAR(32) NOT NULL,
                    quantity DOUBLE NOT NULL,
                    intended_price DOUBLE NOT NULL,
                    executed_price DOUBLE,
                    sl DOUBLE,
                    tp DOUBLE,
                    status VARCHAR(32) NOT NULL,
                    broker_status VARCHAR(32),
                    failure_reason TEXT,
                    strategy VARCHAR(64),
                    created_at VARCHAR(32) NOT NULL,
                    updated_at VARCHAR(32) NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            # 4. Order State Transitions Journal
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS order_transitions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    order_id VARCHAR(64) NOT NULL,
                    from_status VARCHAR(32) NOT NULL,
                    to_status VARCHAR(32) NOT NULL,
                    reason TEXT,
                    timestamp VARCHAR(32) NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            # 5. Active Confirmed Open Positions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS active_positions (
                    id VARCHAR(64) PRIMARY KEY,
                    order_id VARCHAR(64),
                    broker_order_id VARCHAR(64),
                    symbol VARCHAR(32) NOT NULL,
                    direction VARCHAR(16) NOT NULL,
                    size DOUBLE NOT NULL,
                    entry_price DOUBLE NOT NULL,
                    current_price DOUBLE NOT NULL,
                    sl DOUBLE,
                    tp DOUBLE,
                    unrealized_pnl DOUBLE DEFAULT 0.0,
                    open_time VARCHAR(32) NOT NULL,
                    strategy VARCHAR(64) NOT NULL,
                    regime VARCHAR(64),
                    broker_ticket VARCHAR(64),
                    dxy_at_entry DOUBLE,
                    features_json TEXT
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            # 6. Historical Closed Trades Ledger
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id VARCHAR(64) PRIMARY KEY,
                    order_id VARCHAR(64),
                    broker_order_id VARCHAR(64),
                    symbol VARCHAR(32) NOT NULL,
                    side VARCHAR(16),
                    direction VARCHAR(16),
                    quantity DOUBLE,
                    size DOUBLE,
                    entry_price DOUBLE NOT NULL,
                    exit_price DOUBLE,
                    close_price DOUBLE,
                    sl DOUBLE,
                    tp DOUBLE,
                    gross_pnl DOUBLE DEFAULT 0.0,
                    net_pnl DOUBLE DEFAULT 0.0,
                    pnl DOUBLE DEFAULT 0.0,
                    return_pct DOUBLE DEFAULT 0.0,
                    entry_time VARCHAR(32),
                    open_time VARCHAR(32),
                    exit_time VARCHAR(32),
                    close_time VARCHAR(32),
                    strategy VARCHAR(64),
                    market_regime VARCHAR(64),
                    regime VARCHAR(64),
                    confidence DOUBLE,
                    dxy_at_entry DOUBLE,
                    exit_reason TEXT,
                    was_wrong_trade INT DEFAULT 0,
                    loss_cause TEXT,
                    status VARCHAR(32) DEFAULT 'OPEN',
                    broker_ticket VARCHAR(64),
                    features_json TEXT
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            # 7. Immutable Security & Operational Audit Log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id VARCHAR(64) PRIMARY KEY,
                    timestamp VARCHAR(32) NOT NULL,
                    actor_id VARCHAR(64) NOT NULL,
                    actor_role VARCHAR(32) NOT NULL,
                    action VARCHAR(64) NOT NULL,
                    target VARCHAR(64) NOT NULL,
                    old_val TEXT,
                    new_val TEXT,
                    result VARCHAR(32) NOT NULL,
                    client_ip VARCHAR(64),
                    correlation_id VARCHAR(64)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            # 8. Model Registry Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_registry (
                    id VARCHAR(64) PRIMARY KEY,
                    version VARCHAR(32) NOT NULL,
                    model_type VARCHAR(64) NOT NULL,
                    stage VARCHAR(32) NOT NULL,
                    code_sha VARCHAR(64),
                    dataset_version VARCHAR(32),
                    feature_version VARCHAR(32) NOT NULL,
                    training_timestamp VARCHAR(32) NOT NULL,
                    hyperparameters TEXT,
                    validation_accuracy DOUBLE NOT NULL,
                    brier_score DOUBLE NOT NULL,
                    log_loss DOUBLE NOT NULL,
                    artifact_hash VARCHAR(128) NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            # 9. Broker Reconciliation Incidents Log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reconciliation_incidents (
                    id VARCHAR(64) PRIMARY KEY,
                    incident_type VARCHAR(64) NOT NULL,
                    symbol VARCHAR(32),
                    internal_order_id VARCHAR(64),
                    broker_order_id VARCHAR(64),
                    discrepancy_details TEXT NOT NULL,
                    status VARCHAR(32) NOT NULL,
                    created_at VARCHAR(32) NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            # 10. Account Equity & Risk Snapshot Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS account_snapshots (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    timestamp VARCHAR(32) NOT NULL,
                    balance DOUBLE NOT NULL,
                    equity DOUBLE NOT NULL,
                    unrealized_pnl DOUBLE NOT NULL,
                    realized_pnl DOUBLE NOT NULL,
                    daily_starting_equity DOUBLE NOT NULL,
                    drawdown_limit_hit INT DEFAULT 0
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            conn.commit()
            conn.close()
            print(f"[Database] [OK] MySQL database `{self.mysql_db}` initialized successfully on {self.mysql_host}:{self.mysql_port}.")
        except Exception as e:
            print(f"[Database] [WARN] MySQL initialization warning: {e}. Falling back to SQLite.")
            self._init_sqlite_database()

    def _init_sqlite_database(self):
        conn = self._get_sqlite_connection()
        cursor = conn.cursor()

        # 1. Users Table for RBAC
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('READ_ONLY', 'TRADER', 'ADMIN')),
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                last_login TEXT
            );
        """)

        # 2. Authenticated Active Sessions & Tokens
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS active_sessions (
                token_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                is_revoked INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        # 3. Orders Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                client_order_id TEXT UNIQUE NOT NULL,
                broker_order_id TEXT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL CHECK(side IN ('BUY', 'SELL')),
                order_type TEXT NOT NULL,
                quantity REAL NOT NULL,
                intended_price REAL NOT NULL,
                executed_price REAL,
                sl REAL,
                tp REAL,
                status TEXT NOT NULL,
                broker_status TEXT,
                failure_reason TEXT,
                strategy TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)

        # 4. Order State Transitions Journal
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_transitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                from_status TEXT NOT NULL,
                to_status TEXT NOT NULL,
                reason TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
            );
        """)

        # 5. Active Confirmed Open Positions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS active_positions (
                id TEXT PRIMARY KEY,
                order_id TEXT,
                broker_order_id TEXT,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                size REAL NOT NULL,
                entry_price REAL NOT NULL,
                current_price REAL NOT NULL,
                sl REAL,
                tp REAL,
                unrealized_pnl REAL DEFAULT 0.0,
                open_time TEXT NOT NULL,
                strategy TEXT NOT NULL,
                regime TEXT,
                broker_ticket TEXT,
                dxy_at_entry REAL,
                features_json TEXT
            );
        """)

        # 6. Historical Closed Trades Ledger
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id TEXT PRIMARY KEY,
                order_id TEXT,
                broker_order_id TEXT,
                symbol TEXT NOT NULL,
                side TEXT,
                direction TEXT,
                quantity REAL,
                size REAL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                close_price REAL,
                sl REAL,
                tp REAL,
                gross_pnl REAL DEFAULT 0.0,
                net_pnl REAL DEFAULT 0.0,
                pnl REAL DEFAULT 0.0,
                return_pct REAL DEFAULT 0.0,
                entry_time TEXT,
                open_time TEXT,
                exit_time TEXT,
                close_time TEXT,
                strategy TEXT,
                market_regime TEXT,
                regime TEXT,
                confidence REAL,
                dxy_at_entry REAL,
                exit_reason TEXT,
                was_wrong_trade INTEGER DEFAULT 0,
                loss_cause TEXT,
                status TEXT DEFAULT 'OPEN',
                broker_ticket TEXT,
                features_json TEXT
            );
        """)

        # 7. Immutable Security & Operational Audit Log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                actor_role TEXT NOT NULL,
                action TEXT NOT NULL,
                target TEXT NOT NULL,
                old_val TEXT,
                new_val TEXT,
                result TEXT NOT NULL,
                client_ip TEXT,
                correlation_id TEXT
            );
        """)

        # 8. Model Registry Table
        try:
            cursor.execute("PRAGMA table_info(model_registry);")
            cols = [r[1] for r in cursor.fetchall()]
            if cols and "stage" not in cols:
                cursor.execute("DROP TABLE model_registry;")
        except Exception:
            pass

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_registry (
                id TEXT PRIMARY KEY,
                version TEXT NOT NULL,
                model_type TEXT NOT NULL,
                stage TEXT NOT NULL CHECK(stage IN ('CHAMPION', 'CHALLENGER', 'ARCHIVED', 'ROLLED_BACK')),
                code_sha TEXT,
                dataset_version TEXT,
                feature_version TEXT NOT NULL,
                training_timestamp TEXT NOT NULL,
                hyperparameters TEXT,
                validation_accuracy REAL NOT NULL,
                brier_score REAL NOT NULL,
                log_loss REAL NOT NULL,
                artifact_hash TEXT NOT NULL
            );
        """)

        # 9. Broker Reconciliation Incidents Log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reconciliation_incidents (
                id TEXT PRIMARY KEY,
                incident_type TEXT NOT NULL,
                symbol TEXT,
                internal_order_id TEXT,
                broker_order_id TEXT,
                discrepancy_details TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)

        # 10. Account Equity & Risk Snapshot Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS account_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                balance REAL NOT NULL,
                equity REAL NOT NULL,
                unrealized_pnl REAL NOT NULL,
                realized_pnl REAL NOT NULL,
                daily_starting_equity REAL NOT NULL,
                drawdown_limit_hit INTEGER DEFAULT 0
            );
        """)

        conn.commit()
        conn.close()

db = Database()
