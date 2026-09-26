# ADR-005: Unified Database Layer with SQLite and PostgreSQL Dual-Engine Support

## Status
Accepted

## Context
SQLite is excellent for local development, unit tests, and single-instance deployments, but raw direct SQLite queries in `bot/execution/trade_ledger.py` lacked connection pooling, structured migrations, explicit transaction management, and concurrency controls under simultaneous API/WebSocket and engine access. Furthermore, distributed production deployments require PostgreSQL for centralized telemetry, audit trails, and multi-service scalability.

## Decision
1. **Repository / Abstract Storage Pattern**:
   - Create an abstract database interface (`DatabaseEngine`) handling connection lifecycle, query execution, transactions, and WAL configuration.
   - Support both **SQLite** (with WAL mode, `busy_timeout=5000`, `foreign_keys=ON`) for local/edge deployments and **PostgreSQL** (via `asyncpg` / `psycopg2`) for enterprise/cloud deployments.
2. **Deterministic Schema Migration System**:
   - Embed lightweight automated migrations that verify and apply schema versions sequentially without external manual tooling required for container boot.
3. **Transactional Safety**:
   - Order creation, balance deduction, position state transitions, and audit records are wrapped in explicit database transactions to prevent partial write corruptions.

## Consequences
- Allows developers to run the full application locally with zero external dependencies (pure SQLite), while providing seamless PostgreSQL connection when `DATABASE_URL` points to an external Postgres instance.
