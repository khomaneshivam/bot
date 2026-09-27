import time
import uuid
from typing import Optional, Dict
from bot.storage.db import db
from bot.execution.models import OrderStatus, OrderRequest, OrderResult, LEGAL_TRANSITIONS

class OrderStateMachine:
    """
    Deterministic Order State Machine with transition validation and persistent journaling.
    Protects against duplicate submissions (idempotency) and invalid lifecycle transitions.
    """
    def create_order(self, request: OrderRequest) -> Dict:
        """
        Creates an initial CREATED order or returns existing order if client_order_id matches (Idempotency).
        """
        conn = db.get_connection()
        cursor = conn.cursor()

        # Check existing order by client_order_id (Idempotency)
        cursor.execute("SELECT * FROM orders WHERE client_order_id = ?", (request.client_order_id,))
        existing = cursor.fetchone()
        if existing:
            conn.close()
            return dict(existing)

        order_id = f"ord_{uuid.uuid4().hex[:12]}"
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO orders (
                id, client_order_id, symbol, side, order_type, quantity,
                intended_price, sl, tp, status, strategy, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_id, request.client_order_id, request.symbol, request.side,
            request.order_type, request.quantity, request.intended_price,
            request.sl, request.tp, OrderStatus.CREATED.value,
            request.strategy, now, now
        ))

        cursor.execute("""
            INSERT INTO order_transitions (order_id, from_status, to_status, reason, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (order_id, "NONE", OrderStatus.CREATED.value, "Order initialized", now))

        conn.commit()
        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        created = dict(cursor.fetchone())
        conn.close()
        return created

    def transition(
        self,
        order_id: str,
        to_status: OrderStatus,
        reason: str = "",
        broker_order_id: Optional[str] = None,
        executed_price: Optional[float] = None,
        failure_reason: Optional[str] = None
    ) -> bool:
        """
        Validates legal transition, updates orders table, and records immutable transition journal.
        """
        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT status FROM orders WHERE id = ?", (order_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise ValueError(f"Order #{order_id} does not exist")

        current_status = OrderStatus(row["status"])

        # Check legal transitions
        allowed = LEGAL_TRANSITIONS.get(current_status, set())
        if to_status not in allowed:
            conn.close()
            raise ValueError(f"Illegal order state transition: {current_status.value} -> {to_status.value}")

        now = time.strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            UPDATE orders SET
                status = ?,
                broker_order_id = COALESCE(?, broker_order_id),
                executed_price = COALESCE(?, executed_price),
                failure_reason = COALESCE(?, failure_reason),
                updated_at = ?
            WHERE id = ?
        """, (
            to_status.value,
            broker_order_id,
            executed_price,
            failure_reason,
            now,
            order_id
        ))

        cursor.execute("""
            INSERT INTO order_transitions (order_id, from_status, to_status, reason, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (order_id, current_status.value, to_status.value, reason, now))

        conn.commit()
        conn.close()
        return True

    def get_order(self, order_id: str) -> Optional[Dict]:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_order_by_client_id(self, client_order_id: str) -> Optional[Dict]:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE client_order_id = ?", (client_order_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

order_state_machine = OrderStateMachine()
