import os
import sqlite3
import json
import time
from typing import Dict, List, Optional

DB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
DB_PATH = os.path.join(DB_DIR, "quant_trade_ledger.db")

class TradeLedger:
    def __init__(self):
        os.makedirs(DB_DIR, exist_ok=True)
        self.db_path = DB_PATH
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initializes tables for institutional trade ledger and risk audit logs."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Trades Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                market_type TEXT NOT NULL,
                direction TEXT NOT NULL,
                size REAL NOT NULL,
                entry_price REAL NOT NULL,
                close_price REAL,
                sl REAL,
                tp REAL,
                pnl REAL DEFAULT 0.0,
                return_pct REAL DEFAULT 0.0,
                open_time TEXT NOT NULL,
                close_time TEXT,
                strategy TEXT NOT NULL,
                regime TEXT,
                confidence REAL,
                dxy_at_entry REAL,
                exit_reason TEXT,
                was_wrong_trade INTEGER DEFAULT 0,
                retrained_on_mistake INTEGER DEFAULT 0,
                loss_cause TEXT,
                features_json TEXT
            )
        """)

        # Risk Audit Logs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS risk_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                symbol TEXT,
                details TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()

    def log_trade_opened(
        self,
        trade_id: str,
        symbol: str,
        direction: str,
        size: float,
        entry_price: float,
        sl: float,
        tp: float,
        strategy: str,
        regime: str,
        confidence: float,
        dxy_val: float,
        features: Optional[list] = None
    ):
        """Logs a newly executed position into persistent ledger."""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        market_type = "CRYPTO" if "USDT" in symbol else "FOREX"
        feat_json = json.dumps(features) if features else "[]"

        cursor.execute("""
            INSERT OR REPLACE INTO trades (
                id, symbol, market_type, direction, size, entry_price,
                sl, tp, open_time, strategy, regime, confidence,
                dxy_at_entry, features_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade_id, symbol, market_type, direction, size, entry_price,
            sl, tp, now, strategy, regime, confidence, dxy_val, feat_json
        ))
        conn.commit()
        conn.close()

    def log_trade_closed(
        self,
        trade_id: str,
        close_price: float,
        pnl: float,
        exit_reason: str,
        loss_cause: Optional[str] = None
    ):
        """Updates trade record on exit, calculating exact returns and mistake audit flag."""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        # Fetch original trade to compute return %
        cursor.execute("SELECT entry_price, size, direction FROM trades WHERE id = ?", (trade_id,))
        row = cursor.fetchone()
        ret_pct = 0.0
        if row and row["entry_price"] > 0:
            entry = row["entry_price"]
            if row["direction"] == "BUY":
                ret_pct = round(((close_price - entry) / entry) * 100, 2)
            else:
                ret_pct = round(((entry - close_price) / entry) * 100, 2)

        was_wrong = 1 if pnl < 0 else 0

        cursor.execute("""
            UPDATE trades SET
                close_price = ?,
                pnl = ?,
                return_pct = ?,
                close_time = ?,
                exit_reason = ?,
                was_wrong_trade = ?,
                loss_cause = ?
            WHERE id = ?
        """, (close_price, pnl, ret_pct, now, exit_reason, was_wrong, loss_cause or "", trade_id))

        conn.commit()
        conn.close()

    def log_risk_event(self, event_type: str, symbol: str, details: str):
        """Records an institutional safety veto or risk event."""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO risk_audit (timestamp, event_type, symbol, details)
            VALUES (?, ?, ?, ?)
        """, (now, event_type, symbol, details))
        conn.commit()
        conn.close()

    def reset_ledger(self):
        """Resets trade records and risk audit log for clean capital cycles."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM trades")
        cursor.execute("DELETE FROM risk_audit")
        conn.commit()
        conn.close()

    def get_recent_trades(self, limit: int = 50) -> List[Dict]:
        """Returns the latest executed trades formatted for the dashboard."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, symbol, market_type, direction, size, entry_price, close_price,
                   sl, tp, pnl, return_pct, open_time, close_time, strategy,
                   regime, exit_reason, was_wrong_trade, loss_cause
            FROM trades
            ORDER BY open_time DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        trades = [dict(r) for r in rows]
        conn.close()
        return trades

    def get_audit_summary(self) -> Dict:
        """Computes institutional quantitative metrics."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as total, SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins, SUM(pnl) as net_pnl, SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END) as gross_profit, SUM(CASE WHEN pnl < 0 THEN pnl ELSE 0 END) as gross_loss FROM trades WHERE close_price IS NOT NULL")
        row = cursor.fetchone()

        total = row["total"] or 0
        wins = row["wins"] or 0
        losses = total - wins
        net_pnl = round(row["net_pnl"] or 0.0, 2)
        gross_profit = row["gross_profit"] or 0.0
        gross_loss = abs(row["gross_loss"] or 0.0)

        win_rate = round((wins / total * 100), 1) if total > 0 else 0.0
        profit_factor = round(gross_profit / (gross_loss + 1e-8), 2) if gross_loss > 0 else (1.0 if gross_profit == 0 else 9.99)

        # Count risk audit vetoes
        cursor.execute("SELECT COUNT(*) as veto_count FROM risk_audit")
        veto_count = cursor.fetchone()["veto_count"] or 0

        conn.close()
        return {
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "net_pnl": net_pnl,
            "profit_factor": profit_factor,
            "risk_vetoes_count": veto_count
        }

    def get_all_trades(self, limit: int = 500) -> List[Dict]:
        """Returns exhaustive list of all trades with complete metadata."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, symbol, market_type, direction, size, entry_price, close_price,
                   sl, tp, pnl, return_pct, open_time, close_time, strategy,
                   regime, confidence, dxy_at_entry, exit_reason, was_wrong_trade,
                   retrained_on_mistake, loss_cause
            FROM trades
            ORDER BY open_time DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        trades = [dict(r) for r in rows]
        conn.close()
        return trades

    def get_trade_by_id(self, trade_id: str) -> Optional[Dict]:
        """Fetches full trade record including serialized entry feature vectors."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            d = dict(row)
            if d.get("features_json"):
                try:
                    d["features"] = json.loads(d["features_json"])
                except Exception:
                    d["features"] = []
            return d
        return None

    def export_trades_csv(self) -> str:
        """Exports all trades to standard CSV format."""
        import csv
        import io
        trades = self.get_all_trades(limit=2000)
        output = io.StringIO()
        fieldnames = [
            "id", "symbol", "market_type", "direction", "size",
            "entry_price", "close_price", "sl", "tp", "pnl", "return_pct",
            "open_time", "close_time", "strategy", "regime", "confidence",
            "dxy_at_entry", "exit_reason", "loss_cause"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for t in trades:
            writer.writerow(t)
        return output.getvalue()

trade_ledger = TradeLedger()
