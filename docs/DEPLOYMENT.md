# Production Deployment, Hardening & Topology

## 1. Network Topology & Ingress Architecture

In production, the FastAPI application **must never be bound directly to public interface `0.0.0.0:8000`**.

```
                PUBLIC INTERNET (HTTPS / WSS)
                              |
                     Port 443 | Port 80 (Redirect to 443)
                              v
             +----------------------------------+
             |         NGINX GATEWAY            |
             | - SSL/TLS (TLSv1.2, TLSv1.3)    |
             | - HSTS (Strict-Transport-Sec)    |
             | - Rate Limiting (10 req/s IP)    |
             | - WebSocket Upgrade Header Map   |
             | - Static Asset Cache (/dist)     |
             +----------------------------------+
                              |
               Internal Proxy | Unix Socket / 127.0.0.1:8000
                              v
             +----------------------------------+
             |         FASTAPI BACKEND          |
             | - Bound strictly to 127.0.0.1    |
             | - Non-root container user (1001) |
             | - Read-only filesystem except    |
             |   mounted /app/data volume       |
             +----------------------------------+
```

---

## 2. Hardened Dockerfile Architecture

Production containerization follows CIS Docker benchmark guidelines:
1. **Multi-Stage Build**: Node 20 alpine compiles React 18 client; Python 3.11-slim runtime image contains **zero** Node.js or development compilers (`gcc`, `g++`, `make` removed in runtime).
2. **Non-Root Execution**: Runs under dedicated unprivileged user `quantai` (UID 1001).
3. **Healthcheck**: Uses internal Python healthcheck script probing `/api/health` without requiring external `curl`.
4. **Read-Only Root Filesystem**: Application code in `/app` is immutable at runtime; only `/app/data` is mounted writable for the SQLite WAL ledger.

---

## 3. Deployment Environments

| Environment | Mode | Broker Adapter | Auth Enforced? | External Network |
| :--- | :--- | :--- | :---: | :--- |
| **Local Dev** | `PAPER` | `PaperExecutionAdapter` | Optional | Direct localhost:8000 |
| **Staging / Test** | `MT5_DEMO` / `BINANCE_TESTNET` | `MT5ExecutionAdapter` / `BinanceAdapter` | Enforced | Nginx HTTPS Reverse Proxy |
| **Production** | `MT5_LIVE` / `BINANCE_LIVE` | Authenticated Adapters | Strict RBAC | HTTPS (443) + Firewall Lockdown |
