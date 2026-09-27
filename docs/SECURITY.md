# Security Architecture, Threat Model & Controls

## 1. Threat Modeling & Attack Surfaces

| Attack Vector | Target Surface | Potential Impact | Production Mitigation |
| :--- | :--- | :--- | :--- |
| **Unauthenticated Command Execution** | REST Control Endpoints (`/api/bot/*`, `/api/mode`, `/api/trade/*`) | Unauthorized trade placement, mode manipulation, capital loss | Cryptographically signed token auth (Bearer token) with granular RBAC |
| **Telemetry & State Snooping** | WebSocket `/ws`, `/api/status`, `/api/trades/all` | Leakage of private account balances, open positions, strategy weights | Authenticated WebSocket handshake; credentials validated prior to payload streaming |
| **Insecure Account Wipeout** | `/api/account/reset` | Complete deletion of trade history and capital ledger | Restricted strictly to `ADMIN` role; dual confirmation + audit log entry |
| **Cross-Origin Hijacking** | Browser / CORS | CSRF / cross-origin state manipulation | Explicit strict CORS whitelist; credentials validation; anti-CSRF headers |
| **Credential / Secret Exposure** | `.env`, Logs, Exception traces | Compromise of broker and AI credentials | Zero secret logging; automated secret redaction; `.gitignore` enforcement; Argon2 / HMAC token storage |
| **Direct Port Probing** | FastAPI port 8000 | Denial of service, unauthenticated brute-force | Reverse proxy (Nginx) binding to localhost/unix socket; Port 8000 closed to public Internet |

---

## 2. Role-Based Access Control (RBAC) Matrix

| Endpoint | Method | Permitted Roles | Description | Audit Logged? |
| :--- | :---: | :--- | :--- | :---: |
| `/api/auth/login` | POST | Anonymous | Authenticates user and issues access token | Yes |
| `/api/auth/me` | GET | `READ_ONLY`, `TRADER`, `ADMIN` | Returns authenticated user profile | No |
| `/api/status` | GET | `READ_ONLY`, `TRADER`, `ADMIN` | Read-only terminal telemetry | No |
| `/api/trades/all` | GET | `READ_ONLY`, `TRADER`, `ADMIN` | Historical ledger read access | No |
| `/api/trades/export` | GET | `READ_ONLY`, `TRADER`, `ADMIN` | Exports trade audit ledger as CSV | Yes |
| `/ws` | WS | `READ_ONLY`, `TRADER`, `ADMIN` | Telemetry stream (read only) | Yes (Connect/Disconnect) |
| `/api/symbol` | POST | `TRADER`, `ADMIN` | Changes active chart/scanner symbol | Yes |
| `/api/trade/manual` | POST | `TRADER`, `ADMIN` | Executes manual trade within risk rules | Yes |
| `/api/position/close` | POST | `TRADER`, `ADMIN` | Closes active position | Yes |
| `/api/bot/start` | POST | `ADMIN` | Starts automated trading loop | Yes |
| `/api/bot/stop` | POST | `ADMIN` | Pauses automated trading loop | Yes |
| `/api/mode` | POST | `ADMIN` | Switches execution mode | Yes |
| `/api/retrain` | POST | `ADMIN` | Triggers model training/validation | Yes |
| `/api/emergency-stop`| POST | `TRADER`, `ADMIN` | Emergency liquidation & freeze | Yes (CRITICAL alert) |
| `/api/account/reset` | POST | `ADMIN` | Wipes/resets ledger & capital | Yes (CRITICAL alert) |

---

## 3. Cryptographic Token & Authentication Implementation

- **Password Hashing**: Argon2id or Scrypt with random 16-byte salts.
- **Session Tokens**: Cryptographically secure 256-bit random tokens or HMAC-SHA256 signed bearer tokens with configurable TTL (default 12 hours) and instant revocation.
- **WebSocket Handshake Security**: Clients must supply `?token=<TOKEN>` or pass `{"action": "authenticate", "token": "..."}` within 5 seconds of connection. Unauthenticated sockets are dropped immediately with code 4401.

---

## 4. Audit Trail Specification

Every state-altering and control action generates an immutable audit record:
```json
{
  "event_id": "audit_9a8b7c6d5e4f",
  "timestamp": "2026-09-26T14:15:00.123456Z",
  "actor_id": "admin_user",
  "actor_role": "ADMIN",
  "action": "SWITCH_MODE",
  "target": "execution_engine",
  "old_value": "PAPER",
  "new_value": "MT5_DEMO",
  "result": "SUCCESS",
  "client_ip": "10.0.1.25",
  "correlation_id": "req_1122334455"
}
```
Audit records are permanently written to SQLite / PostgreSQL table `audit_events` and cannot be deleted via standard API routes.
