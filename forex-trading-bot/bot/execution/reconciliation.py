import time
import uuid
from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel
from bot.storage.db import db
from bot.execution.adapters.base import BaseExecutionAdapter
from bot.execution.models import BrokerPosition, OrderStatus

class ReconciliationDiscrepancy(BaseModel):
    discrepancy_type: str  # MISSING_BROKER_POSITION, UNEXPECTED_BROKER_POSITION, QUANTITY_MISMATCH, SIDE_MISMATCH
    symbol: str
    internal_id: Optional[str] = None
    broker_id: Optional[str] = None
    internal_qty: float = 0.0
    broker_qty: float = 0.0
    details: str

class ReconciliationReport(BaseModel):
    timestamp: str
    is_synchronized: bool
    internal_positions_count: int
    broker_positions_count: int
    discrepancies: List[ReconciliationDiscrepancy]
    actions_taken: List[str]

class ReconciliationService:
    """
    Independent broker reconciliation service.
    Compares internal active positions with ground-truth broker positions.
    Detects orphan positions, volume drift, and unauthorized orders.
    Fails closed: halts new order placement when desynchronization is discovered.
    """

    def __init__(self):
        self.last_report: Optional[ReconciliationReport] = None
        self.has_active_mismatch = False

    def reconcile(self, adapter: BaseExecutionAdapter) -> ReconciliationReport:
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        discrepancies: List[ReconciliationDiscrepancy] = []
        actions: List[str] = []

        # 1. Fetch internal positions from database
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM active_positions")
        internal_rows = [dict(r) for r in cursor.fetchall()]
        conn.close()

        # 2. Fetch broker positions from execution adapter
        broker_positions = adapter.get_open_positions()

        # Map internal by symbol or broker ticket
        internal_by_broker_id: Dict[str, Dict] = {}
        internal_by_symbol: Dict[str, Dict] = {}
        for row in internal_rows:
            if row.get("broker_order_id"):
                internal_by_broker_id[row["broker_order_id"]] = row
            internal_by_symbol[row["symbol"]] = row

        # Map broker positions
        broker_by_id: Dict[str, BrokerPosition] = {p.position_id: p for p in broker_positions}
        broker_by_symbol: Dict[str, BrokerPosition] = {p.symbol: p for p in broker_positions}

        # Check for missing broker positions (Internal says OPEN, Broker says NO)
        for row in internal_rows:
            b_id = row.get("broker_order_id")
            sym = row["symbol"]
            matching_broker_pos = broker_by_id.get(b_id) if b_id else broker_by_symbol.get(sym)

            if not matching_broker_pos:
                disc = ReconciliationDiscrepancy(
                    discrepancy_type="MISSING_BROKER_POSITION",
                    symbol=sym,
                    internal_id=row["id"],
                    broker_id=b_id,
                    internal_qty=float(row["size"]),
                    broker_qty=0.0,
                    details=f"Internal position #{row['id']} on {sym} does not exist on broker!"
                )
                discrepancies.append(disc)
            else:
                # Check quantity and side mismatch
                if abs(float(row["size"]) - matching_broker_pos.volume) > 1e-4:
                    disc = ReconciliationDiscrepancy(
                        discrepancy_type="QUANTITY_MISMATCH",
                        symbol=sym,
                        internal_id=row["id"],
                        broker_id=matching_broker_pos.position_id,
                        internal_qty=float(row["size"]),
                        broker_qty=matching_broker_pos.volume,
                        details=f"Volume mismatch on {sym}: internal {row['size']} vs broker {matching_broker_pos.volume}"
                    )
                    discrepancies.append(disc)

                if row["direction"].upper() != matching_broker_pos.direction.upper():
                    disc = ReconciliationDiscrepancy(
                        discrepancy_type="SIDE_MISMATCH",
                        symbol=sym,
                        internal_id=row["id"],
                        broker_id=matching_broker_pos.position_id,
                        internal_qty=float(row["size"]),
                        broker_qty=matching_broker_pos.volume,
                        details=f"Direction mismatch on {sym}: internal {row['direction']} vs broker {matching_broker_pos.direction}"
                    )
                    discrepancies.append(disc)

        # Check for unexpected broker positions (Broker has position, Internal has none)
        for b_pos in broker_positions:
            matching_internal = internal_by_broker_id.get(b_pos.position_id) or internal_by_symbol.get(b_pos.symbol)
            if not matching_internal:
                disc = ReconciliationDiscrepancy(
                    discrepancy_type="UNEXPECTED_BROKER_POSITION",
                    symbol=b_pos.symbol,
                    broker_id=b_pos.position_id,
                    internal_qty=0.0,
                    broker_qty=b_pos.volume,
                    details=f"Unexpected position #{b_pos.position_id} ({b_pos.direction} {b_pos.volume} {b_pos.symbol}) found on broker!"
                )
                discrepancies.append(disc)

        is_sync = (len(discrepancies) == 0)
        self.has_active_mismatch = not is_sync

        # If mismatch detected, persist incident in DB and raise alert
        if not is_sync:
            actions.append("HALTED_NEW_TRADES")
            conn = db.get_connection()
            cursor = conn.cursor()
            for d in discrepancies:
                inc_id = f"inc_{uuid.uuid4().hex[:10]}"
                cursor.execute("""
                    INSERT INTO reconciliation_incidents (
                        id, incident_type, symbol, internal_order_id, broker_order_id,
                        discrepancy_details, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    inc_id,
                    d.discrepancy_type,
                    d.symbol,
                    d.internal_id,
                    d.broker_id,
                    d.details,
                    "OPEN",
                    now
                ))
            conn.commit()
            conn.close()

        report = ReconciliationReport(
            timestamp=now,
            is_synchronized=is_sync,
            internal_positions_count=len(internal_rows),
            broker_positions_count=len(broker_positions),
            discrepancies=discrepancies,
            actions_taken=actions
        )
        self.last_report = report
        return report

reconciliation_service = ReconciliationService()
