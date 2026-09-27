# ADR-002: Automated Broker Reconciliation & Desynchronization Recovery

## Status
Accepted

## Context
In live trading, discrepancies inevitably emerge between internal application state and broker reality due to network drops, unhandled partial fills, server reboots, manual trader interventions on broker terminals, and margin liquidations. The original system had zero reconciliation mechanisms: if the application was restarted, all active internal positions were dropped from memory, while remaining active at the broker.

## Decision
We implement a dedicated, autonomous **Reconciliation Service (`ReconciliationService`)**:
1. **Three-Way Comparison**:
   - Internal Open Orders vs. Broker Open Orders
   - Internal Open Positions vs. Broker Open Positions
   - Internal Equity/Balance vs. Broker Reported Equity/Balance
2. **Execution Triggers**:
   - **Startup**: Before any trading loop starts, the engine reconciles existing broker positions with persisted local positions.
   - **Periodic Schedule**: Runs every 60 seconds during active market hours.
   - **Post-Failure**: Triggered immediately upon network disconnect, timeout, or broker communication anomaly.
3. **Discrepancy Severity Policies**:
   - **Dangerous Mismatch** (e.g., unexpected broker position, orphan order, side/volume mismatch):
     1. Immediately raise high-severity alert.
     2. Transition execution state to `HALT_NEW_TRADES`.
     3. Mark affected orders as `RECONCILIATION_REQUIRED`.
     4. Log full audit incident record.
     5. Require manual admin resolution or execute safe policy-based liquidation.
   - **Benign Drift** (e.g., minor floating PnL/equity rounding within $0.05):
     - Update local cache with broker truth; record telemetry log.

## Consequences
- Prevents silent accumulation of unmanaged market risk.
- Guarantees broker truth is the supreme authority over local state.
