# Trading Engine Specification

## 1. Quantitative Strategies Architecture

The platform operates an ensemble of 6 distinct quantitative strategies, each independently calculating direction (`BUY`, `SELL`, `HOLD`), raw signal score, and confidence.

### 1.1 Strategy Descriptions
1. **Trend Momentum (`Trend_Momentum`)**:
   - Triple EMA alignment (9 EMA > 21 EMA > 50 EMA for Long; inverse for Short).
   - ADX(14) trend filter (> 22 threshold ensures non-choppy conditions).
   - MACD acceleration vector confirmation.
2. **Mean Reversion (`Mean_Reversion`)**:
   - Bollinger Bands (2.0 Standard Deviations, 20-period).
   - Stochastic Oscillator (%K, %D crosses) combined with RSI(14) overbought (>68) / oversold (<32) extremes.
3. **Volatility Breakout (`Volatility_Breakout`)**:
   - Donchian Channel (20-period highest high / lowest low).
   - Volume surge ratio (> 1.35x 20-period moving average).
   - ATR expansion filter (> 1.1x benchmark).
4. **Smart Money Concepts (`Smart_Money_SMC`)**:
   - Turtle Soup Liquidity Sweeps (trapping retail breakout stops).
   - Fair Value Gap (FVG) 3-candle imbalance retests.
   - Premium vs. Discount zone qualification (above/below 50% range equilibrium).
5. **Correlation & Macro Divergence (`Correlation_Macro`)**:
   - Synthetic US Dollar Index (DXY) lead-lag divergence.
   - Inverse pair confirmation (EURUSD vs USDCHF correlation decoupling).
   - Gold (XAUUSD) vs real yields & dollar index direction.
6. **Statistical Machine Learning Predictor (`AI_Deep_Predictor`)**:
   - HistGradientBoostingClassifier trained on 60+ parameters.
   - Calibrated probability output.

---

## 2. Multi-Strategy Attribution & Consensus

```
                       STRATEGY VOTES
         +---------------------------------------+
         | - Trend_Momentum       (Vote, Conf)   |
         | - Mean_Reversion       (Vote, Conf)   |
         | - Volatility_Breakout  (Vote, Conf)   |
         | - Smart_Money_SMC      (Vote, Conf)   |
         | - Correlation_Macro    (Vote, Conf)   |
         | - AI_Deep_Predictor    (Vote, Conf)   |
         +---------------------------------------+
                            |
                            v
              REGIME-WEIGHTED CONSENSUS
      (Weights adjusted dynamically by detected regime:
       Trend / Chop / High Volatility / Squeeze)
                            |
                            v
           NEGATIVE EXPERIENCE SHIELD CHECK
      (Veto if cosine similarity > 82% to past failed trade)
                            |
                            v
             TRADER PSYCHOLOGY GUARD CHECK
      (Veto if FOMO, revenge, tilt, or max streak breach)
                            |
                            v
               DETERMINISTIC RISK CHECK
                            |
                            v
                 ORDER STATE MACHINE
```

### 2.1 Strategy Attribution Rules
Every executed trade records:
- `strategy`: Primary winning strategy or `Ensemble`
- `strategy_version`: Git commit SHA of strategy module
- `votes`: Serialized dictionary of all 6 strategy signals and confidence levels at the precise moment of execution.
- `marginal_contribution`: PnL attributed specifically to the strategy's weighted score.
