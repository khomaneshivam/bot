import json
import time
from typing import Dict, List, Optional
from bot.storage.db import db

class TradeLedger:
    """
    Institutional trade ledger and risk audit log unified on the primary platform Database layer.
    Persists across process restarts and container deployments in MySQL InnoDB.
    """
    def __init__(self):
        self.db = db

    def _get_connection(self):
        return self.db.get_connection()

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
                id, order_id, symbol, market_type, side, direction, size, quantity, entry_price,
                sl, tp, open_time, entry_time, strategy, regime, market_regime, confidence,
                dxy_at_entry, features_json, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade_id, trade_id, symbol, market_type, direction.upper(), direction.upper(),
            size, size, entry_price, sl, tp, now, now, strategy, regime, regime,
            confidence, dxy_val, feat_json, "OPEN"
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
        cursor.execute("SELECT entry_price, size, direction, side FROM trades WHERE id = ?", (trade_id,))
        row = cursor.fetchone()
        ret_pct = 0.0
        if row and row["entry_price"] and row["entry_price"] > 0:
            entry = float(row["entry_price"])
            direction = str(row["direction"] or row.get("side", "BUY")).upper()
            if direction == "BUY":
                ret_pct = round(((close_price - entry) / entry) * 100, 2)
            else:
                ret_pct = round(((entry - close_price) / entry) * 100, 2)

        was_wrong = 1 if pnl < 0 else 0

        cursor.execute("""
            UPDATE trades SET
                close_price = ?,
                exit_price = ?,
                pnl = ?,
                gross_pnl = ?,
                net_pnl = ?,
                return_pct = ?,
                close_time = ?,
                exit_time = ?,
                exit_reason = ?,
                was_wrong_trade = ?,
                loss_cause = ?,
                status = 'CLOSED'
            WHERE id = ?
        """, (
            close_price, close_price, round(pnl, 2), round(pnl, 2), round(pnl, 2),
            ret_pct, now, now, exit_reason, was_wrong, loss_cause or "", trade_id
        ))

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
            SELECT id, symbol,
                   COALESCE(market_type, 'FOREX') as market_type,
                   COALESCE(direction, side) as direction,
                   COALESCE(size, quantity) as size,
                   entry_price,
                   COALESCE(close_price, exit_price) as close_price,
                   sl, tp,
                   COALESCE(net_pnl, pnl) as pnl,
                   return_pct,
                   COALESCE(open_time, entry_time) as open_time,
                   COALESCE(close_time, exit_time) as close_time,
                   strategy,
                   COALESCE(regime, market_regime) as regime,
                   exit_reason, was_wrong_trade, loss_cause, status
            FROM trades
            ORDER BY COALESCE(open_time, entry_time) DESC
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

        cursor.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN COALESCE(net_pnl, pnl) > 0 THEN 1 ELSE 0 END) as wins,
                   SUM(COALESCE(net_pnl, pnl)) as net_pnl,
                   SUM(CASE WHEN COALESCE(net_pnl, pnl) > 0 THEN COALESCE(net_pnl, pnl) ELSE 0 END) as gross_profit,
                   SUM(CASE WHEN COALESCE(net_pnl, pnl) < 0 THEN COALESCE(net_pnl, pnl) ELSE 0 END) as gross_loss
            FROM trades
            WHERE (close_price IS NOT NULL OR exit_price IS NOT NULL OR status = 'CLOSED')
        """)
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
        veto_row = cursor.fetchone()
        veto_count = (veto_row["veto_count"] if veto_row else 0) or 0

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
            SELECT id, symbol,
                   COALESCE(market_type, 'FOREX') as market_type,
                   COALESCE(direction, side) as direction,
                   COALESCE(size, quantity) as size,
                   entry_price,
                   COALESCE(close_price, exit_price) as close_price,
                   sl, tp,
                   COALESCE(net_pnl, pnl) as pnl,
                   return_pct,
                   COALESCE(open_time, entry_time) as open_time,
                   COALESCE(close_time, exit_time) as close_time,
                   strategy,
                   COALESCE(regime, market_regime) as regime,
                   confidence, dxy_at_entry, exit_reason, was_wrong_trade,
                   loss_cause, status
            FROM trades
            ORDER BY COALESCE(open_time, entry_time) DESC
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

