# ADR-003: State Machine Persistence & Crash-Resilient Trading State

## Status
Accepted

## Context
The legacy application stored active positions and order state in volatile Python memory (`self.open_positions = []`), while SQLite was used only for historical reporting. Furthermore, the application startup event (`@app.on_event("startup")`) unconditionally wiped the entire database by calling `reset_ledger()`.

## Decision
1. **Persistent State Machine (`OrderStateMachine`)**:
   - Every order transition (`CREATED` ➔ `RISK_APPROVED` ➔ `SUBMITTED` ➔ `ACKNOWLEDGED` ➔ `FILLED` / `REJECTED` / `CANCELLED`) is immutably persisted to disk in the state transition journal.
   - Active open positions are stored with primary keys in the database table `active_positions`.
2. **Elimination of Startup Resets**:
   - `reset_capital()` and `reset_ledger()` are strictly decoupled from application boot.
   - On application startup, the engine executes a deterministic **Recovery Sequence**:
     1. Initialize database and verify schema migrations.
     2. Load active positions, open orders, and risk baselines from storage.
     3. Connect broker adapter.
     4. Execute broker reconciliation.
     5. Re-attach monitoring tasks to reconciled positions.
     6. Only then enable automated strategy evaluation.
3. **Privileged Explicit Account Reset**:
   - Account reset is reserved strictly for authenticated `ADMIN` users via dedicated endpoint `/api/account/reset`, requiring dual confirmation and writing an audit event.

## Consequences
- Guaranteed zero data loss across process crashes, container restarts, or host OS reboots.
- State persistence adds minor I/O latency (< 2ms with WAL mode), easily acceptable for 1m-1h timeframe execution.
