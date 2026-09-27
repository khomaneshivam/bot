# ADR-001: Execution Engine Adapter Architecture & Broker Decoupling

## Status
Accepted

## Context
The previous execution architecture in `bot/execution/engine.py` was tightly coupled to MetaTrader 5 via direct inline calls and a hardcoded simulation fallback. It lacked a unified broker interface, did not support Binance order placement, and violated the Single Responsibility Principle by combining risk gating, order routing, PnL calculations, trailing stop checks, and ML retraining triggers in one file. Crucially, when an MT5 broker order submission failed, the system fell back to "simulated tracking" and created an internal position as if the trade had succeeded.

## Decision
We decouple execution into an explicit **Adapter Pattern** with a stable, abstract broker contract (`BaseExecutionAdapter`):
1. **Core Adapter Contract**:
   - `submit_order(order: OrderRequest) -> OrderResult`
   - `cancel_order(broker_order_id: str) -> bool`
   - `get_order_status(broker_order_id: str) -> OrderStatus`
   - `get_open_positions() -> List[BrokerPosition]`
   - `get_account_balance() -> AccountBalance`
   - `close_position(symbol: str, position_id: str, volume: float) -> CloseResult`
   - `get_symbol_specification(symbol: str) -> InstrumentSpecification`
2. **Concrete Implementations**:
   - `PaperExecutionAdapter`: Realistic simulation modeling bid/ask spreads, slippage, commission, and latency.
   - `MT5ExecutionAdapter`: MetaTrader 5 IPC driver with strict error propagation and no silent simulation fallback.
   - `BinanceExecutionAdapter`: Binance REST/WebSocket execution with authenticated HMAC signatures.
3. **Execution Routing Service (`ExecutionService`)**:
   - Routes orders to the active configured adapter.
   - Manages the Order State Machine.
   - Enforces fail-closed semantics: any broker failure or unknown result triggers an explicit `REJECTED` or `RECONCILIATION_REQUIRED` state—never a confirmed internal position.

## Consequences
- **Positive**: Complete separation between broker protocols and trading logic; eliminates ghost positions; enables independent unit testing with mocked adapters.
- **Negative**: Requires explicit data translation models between broker types and internal canonical structures.
