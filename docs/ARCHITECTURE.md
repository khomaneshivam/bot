# QuantAI Architecture Specification

## 1. System Overview & Architectural Topology

QuantAI is an institutional-grade, multi-asset autonomous quantitative trading terminal engineered for real-time market data ingestion, algorithmic signal evaluation, statistical machine learning inference, deterministic risk enforcement, and broker execution across Forex and cryptocurrency markets.

```
                                  PUBLIC INTERNET
                                         |
                                     HTTPS (443)
                                         |
                     +---------------------------------------+
                     |         NGINX / REVERSE PROXY         |
                     |  - TLS Termination (Let's Encrypt)   |
                     |  - Rate Limiting & Header Hardening   |
                     |  - Static React Assets (/dist)        |
                     +---------------------------------------+
                                         |
                                HTTP (Internal Unix/Local)
                                         |
                     +---------------------------------------+
                     |         FASTAPI GATEWAY (ASGI)        |
                     |  - Auth Middleware & RBAC (Bearer)    |
                     |  - Audit Logging Middleware           |
                     |  - REST Control & Telemetry API       |
                     |  - Authenticated WebSocket Server     |
                     +---------------------------------------+
                                         |
                     +---------------------------------------+
                     |         AUTONOMOUS BOT MANAGER        |
                     |  - Central Event Loop                 |
                     |  - Lifecycle Management               |
                     |  - Real-Time Telemetry Dispatcher     |
                     +---------------------------------------+
                                         |
        +--------------------------------+-------------------------------+
        |                                |                               |
+---------------+               +-----------------+             +-----------------+
|  DATA INGEST  |               | STRATEGY ENGINE |             |    ML ENGINE    |
| - MarketFeed  |               | - Trend Mom.    |             | - Walk-Forward  |
| - DXY Proxy   |               | - Mean Rev.     |             | - Calibration   |
| - Macro News  |               | - Vol Breakout  |             | - Model Reg.    |
| - Real Cal.   |               | - SMC Liquidity |             | - Champion/Chall|
+---------------+               | - Correlation   |             +-----------------+
        \                                |                              /
         +-------------------------------+-----------------------------+
                                         |
                     +---------------------------------------+
                     |       DETERMINISTIC RISK ENGINE       |
                     |  - Broker-Aware Position Sizing       |
                     |  - Daily Drawdown & Exposure Gates    |
                     |  - Spread & Volatility Protection     |
                     |  - Hard Independent Circuit Breaker   |
                     +---------------------------------------+
                                         | (Approved Orders Only)
                     +---------------------------------------+
                     |       ORDER STATE MACHINE & ROUTER    |
                     |  - Legal Transition Validator         |
                     |  - Idempotent Client Order IDs        |
                     |  - Immutable Transition Log           |
                     +---------------------------------------+
                                         |
        +--------------------------------+-------------------------------+
        |                                |                               |
+---------------+               +-----------------+             +-----------------+
| PAPER ADAPTER |               |   MT5 ADAPTER   |             | BINANCE ADAPTER |
| - Slippage    |               | - Native IPC    |             | - Signed REST   |
| - Spread      |               | - Tick Resolv.  |             | - Order WS      |
| - Commissions |               | - Live Accounts |             | - Testnet/Live  |
+---------------+               +-----------------+             +-----------------+
        \                                |                              /
         +-------------------------------+-----------------------------+
                                         |
                     +---------------------------------------+
                     |     BROKER RECONCILIATION ENGINE      |
                     |  - 3-Way Audit (Orders/Positions/Bal) |
                     |  - Startup & Periodic Sync            |
                     |  - Fail-Closed Desync Protection      |
                     +---------------------------------------+
                                         |
                     +---------------------------------------+
                     |       PERSISTENT STORAGE LAYER        |
                     |  - SQLite (WAL Mode) / PostgreSQL     |
                     |  - Active Positions & Order Journal   |
                     |  - User Credentials & RBAC            |
                     |  - Immutable Audit Event Ledger       |
                     +---------------------------------------+
```

---

## 2. Core Functional Layers

### 2.1 Ingestion Layer
- Connects to official public/private feeds (Binance REST/WS, Yahoo Chart API, AlphaVantage/ECB calendar).
- **Zero Fabrication Guarantee**: When market feeds disconnect, the system enters `DATA_STALE` state and refuses trading. Synthetic random-walk generation is strictly eliminated.

### 2.2 Feature & Quantitative Layer
- Computes canonical 60+ parameters: RSI(14), ADX(14), ATR(14), Triple EMAs (9, 21, 50, 200), MACD, Bollinger Bands, Donchian Channels, and Smart Money order blocks.
- Mathematical functions are stateless, pure, and thoroughly unit-tested.

### 2.3 Strategy & AI Layer
- Evaluates 6 distinct quantitative strategies with attribution tracking.
- Google Gemini LLM acts as an asynchronous advisory analyst for macro context and news interpretation; it has **zero authority** to bypass risk rules or directly submit orders.

### 2.4 Risk & Circuit Breaker Layer
- Position sizing calculates instrument-specific tick value, contract size, and base/quote currency conversion.
- Hard circuit breakers immediately halt new entries upon daily drawdown limit, broker desync, or rapid consecutive execution failures.

### 2.5 Execution & Reconciliation Layer
- Decoupled adapters handle broker communication.
- Fail-closed order state machine: Any rejected or unacknowledged broker order transitions to `REJECTED` or `RECONCILIATION_REQUIRED`—never confirming an open position without broker proof.
- Continuous reconciliation ensures internal ledger matches broker reality.

### 2.6 Persistence Layer
- Supports SQLite (with WAL mode, foreign keys, and busy timeout) for local development and PostgreSQL for production.
- Auto-reset upon application startup is completely removed; state is safely restored from the database on boot.
