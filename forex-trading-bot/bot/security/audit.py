import time
import uuid
from typing import Optional
from bot.storage.db import db
from bot.security.models import AuditRecord

class AuditLogger:
    """
    Immutable Audit Logging Service.
    Records every security-sensitive action, mode change, order, and admin event.
    """
    def record(
        self,
        actor_id: str,
        actor_role: str,
        action: str,
        target: str,
        result: str = "SUCCESS",
        old_val: Optional[str] = None,
        new_val: Optional[str] = None,
        client_ip: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> AuditRecord:
        event_id = f"aud_{uuid.uuid4().hex[:12]}"
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_events (
                event_id, timestamp, actor_id, actor_role, action,
                target, old_val, new_val, result, client_ip, correlation_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id, now, actor_id, actor_role, action,
            target, old_val, new_val, result, client_ip, correlation_id
        ))
        conn.commit()
        conn.close()

        record = AuditRecord(
            event_id=event_id,
            timestamp=now,
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            target=target,
            old_val=old_val,
            new_val=new_val,
            result=result,
            client_ip=client_ip,
            correlation_id=correlation_id
        )
        return record

    def log_event(
        self,
        actor_id: str,
        action: str,
        target: str,
        actor_role: str = "SYSTEM",
        result: str = "SUCCESS",
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> AuditRecord:
        return self.record(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            target=target,
            result=result,
            old_val=old_value,
            new_val=new_value,
            client_ip=ip_address,
            correlation_id=correlation_id
        )

    def get_recent_audits(self, limit: int = 100) -> list:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM audit_events
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        audits = [dict(r) for r in rows]
        conn.close()
        return audits

audit_logger = AuditLogger()
