# Deterministic Risk Engine & Hard Circuit Breakers

## 1. Multi-Tier Risk Verification Pipeline

Every order candidate—whether produced by autonomous strategy consensus or submitted via manual trader control—must pass through the **Deterministic Risk Engine** before reaching any execution adapter.

```
Candidate Order
      |
      v
[Rule 1: Hard Kill Switch Active?] -------> REJECT ("CIRCUIT_BREAKER_KILL_SWITCH")
      |
      v
[Rule 2: Daily Drawdown Exceeded?] -------> REJECT ("MAX_DAILY_DRAWDOWN_EXCEEDED")
      |
      v
[Rule 3: Max Open Positions Limit?] ------> REJECT ("MAX_CONCURRENT_POSITIONS_REACHED")
      |
      v
[Rule 4: Same-Symbol Duplicate?] ---------> REJECT ("SYMBOL_ALREADY_OPEN")
      |
      v
[Rule 5: Cross-Asset Correlation?] -------> REJECT ("PORTFOLIO_CORRELATION_VETO")
      |
      v
[Rule 6: Market Data Stale / Offline?] ---> REJECT ("MARKET_DATA_STALE")
      |
      v
[Rule 7: High-Impact Macro News Window?] -> REJECT ("MACRO_NEWS_BLACKOUT_WINDOW")
      |
      v
[Rule 8: Broker Spread Too Wide?] --------> REJECT ("EXCESSIVE_SPREAD")
      |
      v
[Rule 9: Broker-Aware Sizing Valid?] -----> REJECT ("SIZING_OUT_OF_BOUNDS")
      |
      v
ORDER APPROVED FOR ROUTING
```

---

## 2. Institutional Broker-Aware Position Sizing

The simplistic formula `units = risk_amount / (entry - sl)` fails in multi-asset trading. The engine utilizes instrument specifications:

### 2.1 Formula Specifications
$$\text{Risk Cash (USD)} = \text{Account Equity} \times \frac{\text{Max Risk \%}}{100}$$

$$\text{Stop Distance (Points/Pips)} = \frac{|\text{Entry Price} - \text{Stop Loss}|}{\text{Tick Size}}$$

$$\text{Position Size} = \frac{\text{Risk Cash}}{\text{Stop Distance} \times \text{Tick Value} \times \text{Conversion Rate}}$$

### 2.2 Instrument Rules
1. **Forex Currency Pairs** (EURUSD, GBPUSD, AUDUSD):
   - 1 Standard Lot = 100,000 base currency.
   - For USD quote pairs (EUR/USD): 1 pip (0.0001) = $10.00 per lot ($0.10 per 0.01 micro-lot).
   - For USD base pairs (USD/JPY): 1 pip (0.01) = $1,000 JPY / Current USDJPY rate.
   - Quantized to minimum lot step (0.01).
2. **Gold Spot (XAUUSD)**:
   - 1 Standard Lot = 100 troy ounces.
   - $1.00 move per 1.0 lot = $100.00. 0.01 micro-lot = $1.00 per $1.00 gold move.
3. **Cryptocurrency (BTCUSDT, ETHUSDT, SOLUSDT)**:
   - Notional capital cap: Max 40% of total equity per crypto trade.
   - Size quantized to instrument precision (e.g. 0.0001 BTC, 0.01 SOL).

---

## 3. Hard Safety Circuit Breakers

| Condition | Threshold | System Action | Recovery Action |
| :--- | :--- | :--- | :--- |
| **Daily Drawdown Breach** | Equity drops ≥ 5.0% from daily baseline | `HALT_NEW_TRADES`. Liquidate trailing stops only. | Resets only on new trading day (00:00 UTC) with admin review |
| **Broker Position Desynchronization** | Internal vs Broker mismatch detected | `HALT_NEW_TRADES`. Raise P0 alert. | Manual admin reconciliation or automated safe sync |
| **Rapid Execution Failures** | ≥ 3 consecutive broker order rejections | `HALT_NEW_TRADES`. | Verify broker connectivity and credentials |
| **Market Data Staleness** | Feed timestamp older than 60 seconds | Block new entries. | Auto-resumes only when fresh valid tick arrives |
| **Database Transaction Failure** | SQLite/PostgreSQL write timeout/failure | Block execution immediately (fail-closed). | Database health check passes |
