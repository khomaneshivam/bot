# Automated Testing Strategy & Safety Verification

## 1. Testing Pyramid Architecture

```
                    / \
                   /   \
                  /  E2E \              (Failure Injection, Reconnects, System Resiliency)
                 /--------\
                /  Integ.  \            (FastAPI Auth, WebSocket Handshake, SQLite/Postgres)
               /------------\
              /  Property    \          (Deterministic Invariants: Sizing, Zero Ghost Trades)
             /----------------\
            /    Unit Tests    \        (PnL Math, Risk Rules, State Machine, Indicators)
           +--------------------+
```

---

## 2. Core Invariant Properties Tested

1. **Property 1 (Zero Ghost Positions)**:
   - Given a rejected broker order or socket timeout, the engine must never append a position to the open positions list or commit a confirmed trade to the ledger.
2. **Property 2 (RBAC Isolation)**:
   - An unauthenticated user or user with `READ_ONLY` role can never trigger order placement, mode change, bot start/stop, retrain, or account reset.
3. **Property 3 (Drawdown Lock)**:
   - When cumulative daily loss meets or exceeds `MAX_DAILY_DRAWDOWN_PERCENT` (5.0%), all subsequent entry candidates must return `daily_drawdown_limit_hit=True` and be blocked.
4. **Property 4 (State Crash Resilience)**:
   - When the application process is terminated and restarted, active open positions and historical trades must be reloaded without being wiped.
5. **Property 5 (Data Freshness Gate)**:
   - When the latest market tick timestamp is older than 60 seconds, all new trade proposals must be rejected with `MARKET_DATA_STALE`.
6. **Property 6 (Duplicate Idempotency)**:
   - Two concurrent order requests with identical `client_order_id` must result in exactly one broker submission.

---

## 3. Failure Injection Testing Scenarios

- **Broker Timeout Injection**: Simulates network packet loss after order submission. Verifies transition to `RECONCILIATION_REQUIRED`.
- **Unexpected Broker Position**: Injects an unrecorded trade into the mocked broker. Verifies reconciliation engine halts trading and raises P0 incident alert.
- **Corrupt Model File**: Loads an unpickled or corrupted model artifact. Verifies failover to baseline heuristic without crash.
