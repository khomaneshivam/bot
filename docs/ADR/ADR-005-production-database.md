# ADR-005: Unified Database Layer with MySQL 8.0 InnoDB Engine and Connection Pooling

## Status
Accepted

## Context
Raw direct SQLite queries in legacy `bot/execution/trade_ledger.py` created a dual-ledger split-brain architectural defect: `ExecutionService` persisted confirmed orders and active positions into the primary database, while `TradeLedger` read and wrote to a separate local file (`data/quant_trade_ledger.db`). This caused desynchronization across the dashboard, metrics, and quantitative forensics. Furthermore, under autonomous high-frequency polling, opening unpooled TCP connections risked socket exhaustion (TIME_WAIT states).

## Decision
1. **Unified Storage Architecture**:
   - Standardize on **MySQL 8.0 InnoDB** (`trading_bot_db`) as the authoritative production persistence engine.
   - Refactor `TradeLedger` to execute exclusively through the unified `Database` interface (`from bot.storage.db import db`), eliminating all standalone SQLite files in production.
2. **Thread-Safe Connection Pooling**:
   - Implement `MySQLConnectionPool` utilizing a bounded thread-safe queue of reusable `pymysql.Connection` instances with automatic health validation (`conn.ping()`) and dynamic pool recycling.
3. **Fail-Closed Database Policy**:
   - Eliminate silent fallback to SQLite in production. If MySQL is unreachable, the system fails closed, raises a `ConnectionError`, and trips the safety circuit breaker (`DATABASE_DISCONNECTED`). SQLite fallback is strictly prohibited unless `ALLOW_SQLITE_FALLBACK=true` is explicitly configured.
4. **Deterministic Schema & Historical Auditing**:
   - Maintain 11 normalized InnoDB tables: `users`, `active_sessions`, `orders`, `order_transitions`, `active_positions`, `trades`, `audit_events`, `model_registry`, `reconciliation_incidents`, `account_snapshots`, and `risk_audit`.
   - Embed automatic lightweight column migrations (`ALTER TABLE`) directly into database initialization.

## Consequences
- Single authoritative ledger for all orders, trades, quantitative metrics, and audit logs.
- High-frequency resilience under continuous automated cycles and WebSocket telemetry without socket leaks.
- Zero state divergence between execution engine and dashboard reporting.
