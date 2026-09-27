# Production Runbook & Incident Response (OPERATIONS.md)

## 1. Operational Procedures

### 1.1 Cold Startup Procedure
1. Verify environment configuration:
   ```bash
   python -c "from bot.config.settings import settings; print('Mode:', settings.MODE)"
   ```
2. Verify database connectivity & migrations:
   ```bash
   python -m bot.storage.migrator
   ```
3. Start application under systemd or Docker:
   ```bash
   docker compose up -d
   ```
4. Verify broker reconciliation and health check:
   ```bash
   curl -s http://127.0.0.1:8000/api/health
   ```

### 1.2 Graceful Shutdown Procedure
1. Set bot to pause mode via authenticated API:
   ```bash
   curl -X POST http://127.0.0.1:8000/api/bot/stop -H "Authorization: Bearer <ADMIN_TOKEN>"
   ```
2. Allow pending cycle loop tasks to complete (drain period: 10s).
3. Stop container:
   ```bash
   docker compose down
   ```

---

## 2. Emergency Incident Response

### 2.1 Triggering the Hard Kill Switch
If runaway trading, algorithmic malfunction, or exchange flash crash occurs:
```bash
curl -X POST http://127.0.0.1:8000/api/emergency-stop \
  -H "Authorization: Bearer <ADMIN_OR_TRADER_TOKEN>"
```
**Effect**:
- Halts all automated loop tasks immediately.
- Sets `is_running = False`.
- Issues market close orders for all open positions across all active adapters.
- Emits high-priority audit record and metric alert.

### 2.2 Broker Desynchronization Protocol
If a reconciliation alert fires:
1. Review desync report at `/api/reconciliation/status`.
2. Compare tickets against broker terminal (MT5 or Binance Web UI).
3. If ghost position detected on broker, execute manual sync or liquidate via `/api/reconciliation/sync`.
4. Resume trading only after reconciliation reports `clean=True`.

---

## 3. Database Backup & Disaster Recovery

### 3.1 Automated SQLite WAL Backup
Run the backup script:
```bash
bash deploy/backup-db.sh
```
Stores timestamped, validated SQLite snapshots in `/app/backups/`.

### 3.2 Restoration from Backup
```bash
bash deploy/restore-db.sh /app/backups/quant_trade_ledger_20260926_120000.db
```
Restoration script verifies integrity with `PRAGMA integrity_check` before placing into active data directory.
