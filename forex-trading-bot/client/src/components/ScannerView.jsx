/**
 * QuantAI Terminal - 1-Minute Multi-Pair Multi-Strategy Audit Scanner View
 */

import React, { useState, useEffect } from "react";
import { useTrading } from "../context/TradingContext";
import { formatPrice } from "../utils/formatters";

export function ScannerView() {
  const { telemetry, triggerAuditScan, switchSymbol, setActiveView } = useTrading();
  const { audit_matrix } = telemetry;

  const [countdown, setCountdown] = useState(60);

  useEffect(() => {
    if (audit_matrix && typeof audit_matrix.next_audit_sec === "number") {
      setCountdown(audit_matrix.next_audit_sec);
    }
  }, [audit_matrix]);

  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown((prev) => (prev > 1 ? prev - 1 : 60));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const records = audit_matrix ? audit_matrix.audit_records || [] : [];

  const handleSelectSymbol = (sym) => {
    switchSymbol(sym);
    setActiveView("terminal");
  };

  const renderStrategyPill = (strategies, key) => {
    const s = strategies ? strategies[key] || {} : {};
    const sig = s.signal || "HOLD";
    const chance = s.chance_pct || 0;
    let pillClass = "pill-hold";
    if (sig === "BUY") pillClass = "pill-buy";
    if (sig === "SELL") pillClass = "pill-sell";

    return (
      <span className={`strat-mini-pill ${pillClass}`}>
        {sig} {chance}%
      </span>
    );
  };

  return (
    <div className="view-panel active" style={{ display: "block" }}>
      <div className="ledger-view-header">
        <div className="ledger-title-group">
          <h2>
            <span className="header-icon">⚡</span> 1-MINUTE MULTI-PAIR AUDIT SCANNER
          </h2>
          <p>
            Parallel quantitative feasibility scan evaluated across 9 asset pairs and 6 institutional strategy engines every 60 seconds. Next scan in:{" "}
            <strong className="mono" style={{ color: "var(--color-cyan)" }}>
              {countdown}s
            </strong>
          </p>
        </div>
        <div className="ledger-actions-group">
          <button className="btn-ledger-action" onClick={triggerAuditScan}>
            <span>⚡</span> Force Audit Scan Now
          </button>
        </div>
      </div>

      <div className="glass-panel data-card full-width">
        <div className="table-responsive">
          <table className="quant-table">
            <thead>
              <tr>
                <th>Asset Pair</th>
                <th>Price</th>
                <th>Regime</th>
                <th>Trade Feasibility</th>
                <th>Trend Momentum</th>
                <th>Mean Reversion</th>
                <th>Breakout</th>
                <th>Smart Money (SMC)</th>
                <th>Macro DXY</th>
                <th>AI Predictor</th>
                <th>Audit Verdict</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {records.length === 0 ? (
                <tr>
                  <td colSpan="12" className="text-center text-muted">
                    Loading 1-minute scanner telemetry...
                  </td>
                </tr>
              ) : (
                records.map((item) => {
                  const sym = item.symbol;
                  const isCrypto = sym.includes("USDT");
                  const chance = item.overall_chance_pct || 0;

                  let barClass = "chance-grey";
                  if (item.vetoed) barClass = "chance-red";
                  else if (chance >= 65) barClass = "chance-green";
                  else if (chance >= 40) barClass = "chance-yellow";

                  const dirTag =
                    item.overall_signal === "BUY"
                      ? "🟢 BUY"
                      : item.overall_signal === "SELL"
                      ? "🔴 SELL"
                      : "⚪ HOLD";

                  return (
                    <tr key={sym}>
                      <td>
                        <div className="audit-pair-wrap">
                          <span className="audit-pair-name">{sym}</span>
                          <span
                            className="metric-badge"
                            style={{
                              fontSize: "0.6rem",
                              background: isCrypto ? "rgba(0,210,255,0.12)" : "rgba(168,85,247,0.12)",
                              color: isCrypto ? "var(--color-cyan)" : "var(--color-purple)",
                            }}
                          >
                            {isCrypto ? "CRYPTO" : "FOREX"}
                          </span>
                        </div>
                      </td>
                      <td>
                        <strong>{formatPrice(item.price, sym)}</strong>
                      </td>
                      <td>
                        <span className="metric-badge" style={{ fontSize: "0.65rem" }}>
                          {(item.regime || "NEUTRAL").replace(/_/g, " ")}
                        </span>
                      </td>
                      <td>
                        <div className="chance-container">
                          <div className="chance-header">
                            <span>{dirTag}</span>
                            <span>{chance}%</span>
                          </div>
                          <div className="chance-bar-bg">
                            <div
                              className={`chance-bar-fill ${barClass}`}
                              style={{ width: `${chance}%` }}
                            ></div>
                          </div>
                        </div>
                      </td>
                      <td>{renderStrategyPill(item.strategies, "Trend_Momentum")}</td>
                      <td>{renderStrategyPill(item.strategies, "Mean_Reversion")}</td>
                      <td>{renderStrategyPill(item.strategies, "Volatility_Breakout")}</td>
                      <td>{renderStrategyPill(item.strategies, "Smart_Money_SMC")}</td>
                      <td>{renderStrategyPill(item.strategies, "Correlation_Macro")}</td>
                      <td>{renderStrategyPill(item.strategies, "AI_Deep_Predictor")}</td>
                      <td>
                        <span className={item.badge_class || "badge-dormant"}>
                          {item.status_text}
                        </span>
                      </td>
                      <td>
                        <button
                          className="btn-switch-chart"
                          onClick={() => handleSelectSymbol(sym)}
                          title={`Load ${sym} on main chart`}
                        >
                          📈 Chart
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
