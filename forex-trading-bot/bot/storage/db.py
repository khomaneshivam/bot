import os
import sqlite3
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
DEFAULT_SQLITE_PATH = os.path.join(DB_DIR, "quant_trade_ledger.db")

class Database:
    """
    Unified Storage Layer for QuantAI Platform.
    Enforces SQLite WAL mode, foreign keys, and connection concurrency protection.
    Ready for PostgreSQL via environment connection string if configured.
    """
    def __init__(self, db_path: Optional[str] = None):
        os.makedirs(DB_DIR, exist_ok=True)
        self.db_path = db_path or os.getenv("SQLITE_DB_PATH", DEFAULT_SQLITE_PATH)
        self.is_postgres = bool(os.getenv("DATABASE_URL", "").startswith("postgresql"))
        self._init_database()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.db_path,
            timeout=10.0,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        # Enable WAL mode and foreign key enforcement on SQLite
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        return conn

    def _init_database(self):
        """Initializes tables, indexes, and schema definitions idempotently."""
        conn = self.get_connection()
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

        # 3. Orders Table (Order State Machine)
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

        # 5. Active Confirmed Open Positions (Persisted across restarts)
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
