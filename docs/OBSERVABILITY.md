# Observability, Structured Logging & Metrics Specification

## 1. Structured JSON Logging Architecture

All system components emit machine-parseable JSON logs formatted according to the standard institutional schema:
```json
{
  "timestamp": "2026-09-26T14:30:00.123456Z",
  "level": "INFO",
  "service": "execution_engine",
  "event_type": "ORDER_FILLED",
  "correlation_id": "c1d2e3f4-5678",
  "trade_id": "tr_8a9b0c",
  "symbol": "BTCUSDT",
  "message": "Order filled at 84250.00 | Size: 0.01",
  "metadata": {
    "broker": "BINANCE",
    "order_type": "MARKET",
    "fill_price": 84250.00,
    "slippage": 1.20,
    "commission": 0.08
  }
}
```

### 1.1 Log Redaction Safeguards
Log handlers enforce automated regex-based redaction on:
- API Keys (`GEMINI_API_KEY`, `BINANCE_API_KEY`)
- Passwords (`MT5_PASSWORD`, user login passwords)
- Authorization header tokens (`Bearer ...`)

---

## 2. Real-Time Prometheus Metrics

The application exposes a `/metrics` Prometheus endpoint covering key trading system metrics:

| Metric Name | Type | Description |
| :--- | :--- | :--- |
| `quantai_equity_usd` | Gauge | Real-time total portfolio equity in USD |
| `quantai_balance_usd` | Gauge | Cash account balance in USD |
| `quantai_open_positions_count` | Gauge | Number of active open positions |
| `quantai_daily_drawdown_pct` | Gauge | Current daily drawdown percentage |
| `quantai_orders_total` | Counter | Total orders by status (`filled`, `rejected`, `vetoed`) |
| `quantai_risk_vetoes_total` | Counter | Count of risk rejections by rule reason |
| `quantai_execution_latency_seconds`| Histogram | Latency of order routing to broker fill |
| `quantai_reconciliation_mismatches`| Counter | Number of detected broker desync events |
| `quantai_ml_inference_seconds` | Histogram | Latency of feature computation and model prediction |
| `quantai_ws_active_clients` | Gauge | Count of active authenticated WebSocket connections |

---

## 3. Production Alerting Thresholds

- **P0 Critical (Immediate Pager / Slack / Webhook)**:
  - Daily Drawdown ≥ 5.0%
  - Broker Desynchronization (Orphan position or volume mismatch)
  - 3 Consecutive Broker Order Rejections
  - Database Write Failure
- **P1 High Warning**:
  - Market data feed staleness > 45 seconds
  - Gemini API rate limit or persistent timeout
  - High broker spread veto rate (> 5 vetoes in 10 minutes)
