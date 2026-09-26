from prometheus_client import Gauge, Counter, generate_latest, CONTENT_TYPE_LATEST
from typing import Dict, Any

TRADING_EQUITY = Gauge("trading_equity_usd", "Current account equity in USD")
TRADING_BALANCE = Gauge("trading_balance_usd", "Current account balance in USD")
ACTIVE_POSITIONS_COUNT = Gauge("trading_active_positions_count", "Current number of open positions")
CIRCUIT_BREAKER_TRIPPED = Gauge("trading_circuit_breaker_active", "1 if any circuit breaker is active, 0 otherwise")
ORDERS_SUBMITTED = Counter(
    "trading_orders_total",
    "Total orders processed through state machine",
    ["status", "symbol", "side"]
)
RECONCILIATION_INCIDENTS = Counter(
    "trading_reconciliation_incidents_total",
    "Total reconciliation mismatches detected",
    ["discrepancy_type"]
)
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests handled",
    ["method", "endpoint", "status_code"]
)

def update_portfolio_metrics(balance: float, equity: float, active_positions: int, is_tripped: bool):
    TRADING_BALANCE.set(balance)
    TRADING_EQUITY.set(equity)
    ACTIVE_POSITIONS_COUNT.set(active_positions)
    CIRCUIT_BREAKER_TRIPPED.set(1 if is_tripped else 0)

def generate_metrics_output() -> bytes:
    return generate_latest()
