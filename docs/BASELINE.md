# System Baseline & Technical Debt Audit Report

**Date**: 2026-09-26  
**Auditor**: Principal Systems Architect, Quantitative Execution & DevSecOps  
**Repository Branch**: `feature/production-grade-trading-system`  
**Target Revision**: Production-Grade Autonomous Trading Architecture

---

## 1. Environment & Runtime Specifications

| Component | Detected Specification | Note |
| :--- | :--- | :--- |
| **Operating System** | Windows 10/11 Enterprise x86_64 / Target: Ubuntu 24.04 LTS (AWS EC2) | Cross-platform compatibility required |
| **Python Runtime** | Python 3.13.5 (Local development) / 3.11.x (Container target) | Python 3.11-3.13 parity |
| **Node.js / NPM** | Node.js v20.x, NPM v10.x | Client compilation runtime |
| **Container Engine** | Docker Engine 26+, Podman / Buildah (EC2 rootless) | Rootless daemon compatibility |
| **Primary Frameworks** | FastAPI 0.138.0, Uvicorn 0.49.0, Pydantic 2.12.5, Starlette 1.3.1 | Asynchronous ASGI stack |
| **Quantitative / ML** | NumPy 2.2.6, Pandas 2.3.1, Scikit-learn 1.7.1, SciPy 1.16.1, TA 0.11.0 | Machine learning & indicators |
| **Database** | SQLite 3 (`data/quant_trade_ledger.db`) | Target: PostgreSQL / SQLite abstract |
| **Testing Harness** | Pytest 9.1.1, AnyIO 4.10.0, HTTPX 0.28.1 | Automated testing framework |

---

## 2. Baseline Test Execution Results

- **Existing Tests Collected**: `0`
- **Failing Tests**: `0` (None existed)
- **Code Coverage**: `0.0%`
- **Static Analysis / Lint Status**: Not previously configured in CI.

---

## 3. Application Startup & Build Verification

1. **Frontend Compilation (`client`)**:
   - `npm run build` executed successfully producing `dist/index.html` (1.13 kB) and assets (261 kB total).
   - Bundle clean, no fatal compilation errors.

2. **Backend Startup (`server.app`)**:
   - Imports succeeded; pre-warming routine runs on import.
   - **Severe Side Effect on Startup**: `@app.on_event("startup")` executes `execution_engine.reset_capital(100.0)`, which calls `trade_ledger.reset_ledger()` issuing `DELETE FROM trades; DELETE FROM risk_audit;`.
   - Result: Every application reboot, container restart, or crash recovery completely deletes all historical records and resets trading equity.

3. **Container Build Verification**:
   - Multi-stage Dockerfile builds both React client and Python environment.
   - Resource constraint hazard: In low-disk environments (< 2 GB root EBS), Podman/Docker buildah crashes with `write /var/tmp/...: no space left on device` due to unoptimized multi-stage layer commits.

---

## 4. Architectural & Implementation Defects (Audit Findings)

### 🔴 Critical P0 Defects

1. **Critical Live-Execution Ghost Position Bug (`bot/execution/engine.py` L238-241)**:
   - When an order submission to MetaTrader 5 fails or returns an error, the engine logs: `⚠️ MT5 Route: {err}. Operating in simulated tracking.` and proceeds to append the position to `self.open_positions` and SQLite ledger.
   - **Impact**: Failed broker orders are recorded as confirmed open positions. If market moves, the bot believes it holds inventory that does not exist at the broker.

2. **Total Absence of Authentication & RBAC (`server/app.py`)**:
   - All REST endpoints (`/api/account/reset`, `/api/bot/start`, `/api/bot/stop`, `/api/mode`, `/api/symbol`, `/api/trade/manual`, `/api/position/close`, `/api/emergency-stop`) are completely unauthenticated.
   - Any anonymous HTTP client on the network can trigger live market orders, liquidate all positions, or wipe the database.

3. **Unauthenticated Public WebSocket Feed (`/ws`)**:
   - Accepts unauthenticated connections immediately.
   - Broadcasts real-time financial telemetry, full account balances, open positions, and strategy internals without credential validation.

4. **Destructive Auto-Reset on Startup (`server/app.py` L31)**:
   - `execution_engine.reset_capital(settings.PAPER_STARTING_BALANCE)` deletes all trade history and active risk data upon startup.

5. **In-Memory State Volatility (`bot/execution/engine.py`)**:
   - Active open positions exist solely in Python list `self.open_positions`.
   - On crash or reboot, all tracked active positions vanish from engine memory while potentially remaining open at the broker.

6. **Missing Broker Reconciliation Engine**:
   - No mechanism exists to compare internal open positions against broker-confirmed tickets.
   - Desynchronizations, partial fills, manual broker interventions, or orphan orders cannot be detected or resolved.

### 🟠 High Severity (P1) Defects

7. **Synthetic / Fabricated Data Ingestion (`bot/data/market_feed.py` L171-200)**:
   - When public chart APIs fail or cache is cold, the feed generates random synthetic random-walk candles (`delta = (np.random.random() - 0.49) * ...`) and feeds them into ML models and trading strategies.
   - Violation of fail-closed principle.

8. **Fake Real-Time News Injection (`bot/data/news_feed.py` L104, L126-150)**:
   - When external RSS feeds fail, the engine injects static pre-written headlines with `datetime.now(timezone.utc).strftime("%H:%M UTC")` timestamps, masquerading as live breaking news.

9. **ML Lookahead & Train-on-Test Contamination (`bot/ai/ml_engine.py` L111-152)**:
   - Accuracy is evaluated on the exact same dataset used for training (`preds = self.model.predict(X_train_scaled)`).
   - No walk-forward cross-validation or out-of-sample testing.
   - Immediate retraining on individual wrong trades with arbitrary 4x sample weight causes catastrophic model distortion.

10. **Simplistic Risk Sizing (`bot/risk/risk_manager.py`)**:
    - Position sizing ignores contract sizes, tick values, base-vs-quote exchange conversions (e.g. USDJPY, XAUUSD), resulting in inaccurate monetary risk allocation.

11. **Direct Public Exposure of Port 8000**:
    - No reverse proxy (Nginx/ALB), lack of TLS termination, and missing security headers (`HSTS`, `Content-Security-Policy`, `X-Frame-Options`).

---

## 5. Baseline Status

| Acceptance Area | Status | Required Action |
| :--- | :--- | :--- |
| **Authentication & RBAC** | FAILED | Implement token-based auth with RBAC (READ_ONLY, TRADER, ADMIN) |
| **WebSocket Security** | FAILED | Secure handshake with authenticated session control |
| **Fail-Closed Execution** | FAILED | Forbid internal position confirmation on unacknowledged broker orders |
| **Broker Reconciliation** | MISSING | Implement automated 3-way reconciliation (startup + periodic) |
| **State Persistence** | FAILED | Remove startup resets; persist state machine transitions |
| **Risk & Circuit Breakers** | PARTIAL | Add broker-aware sizing and hard independent kill switch |
| **ML/MLOps Governance** | FAILED | Walk-forward validation, model registry, champion/challenger |
| **Test Coverage** | ZERO | Implement unit, integration, failure-injection, and property tests |

**Baseline Assessment**: NOT_READY for production or live execution. Immediate P0 architectural transformation required.
