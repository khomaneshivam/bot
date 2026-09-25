/**
 * QuantAI Terminal - Cross-Asset Correlation & Macro Radar View
 */

import React from "react";
import { useTrading } from "../context/TradingContext";

export function MacroView() {
  const { telemetry } = useTrading();
  const { dxy_proxy, dxy_trend, correlation_matrix } = telemetry;

  const matrix = correlation_matrix || {};
  const symbols = Object.keys(matrix);
  const preferred = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSDT"];
  const displaySyms = preferred.filter((s) => symbols.includes(s));
  for (const s of symbols) {
    if (displaySyms.length < 5 && !displaySyms.includes(s)) {
      displaySyms.push(s);
    }
  }

  return (
    <div className="view-panel active" style={{ display: "block" }}>
      <div className="ledger-view-header">
        <div className="ledger-title-group">
          <h2>
            <span className="header-icon">🌐</span> CROSS-ASSET CORRELATION & MACRO DXY RADAR
          </h2>
          <p>
            Institutional dollar index basket tracking and multi-asset correlation matrices to prevent correlated portfolio drawdowns.
          </p>
        </div>
      </div>

      <div className="grid-2col" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 24 }}>
        {/* DXY Basket Info */}
        <div className="glass-panel data-card">
          <div className="card-header">
            <h2 className="card-title">💵 SYNTHETIC US DOLLAR INDEX (DXY PROXY)</h2>
            <span
              className="card-tag"
              style={{
                color: dxy_trend.includes("BULLISH")
                  ? "var(--color-green)"
                  : dxy_trend.includes("BEARISH")
                  ? "var(--color-red)"
                  : "var(--text-secondary)",
              }}
            >
              {(dxy_trend || "NEUTRAL").replace(/_/g, " ")}
            </span>
          </div>

          <div style={{ fontSize: "2rem", fontWeight: 800, fontFamily: "var(--font-mono)", margin: "14px 0" }}>
            {Number(dxy_proxy || 104.5).toFixed(2)}
          </div>

          <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
            Calculated geometrically using the official Federal Reserve trade-weighted currency weights: EUR (57.6%), JPY (13.6%), GBP (11.9%), CAD (9.1%), SEK (4.2%), CHF (3.6%).
          </p>
        </div>

        {/* Heatmap Matrix */}
        <div className="glass-panel data-card">
          <div className="card-header">
            <h2 className="card-title">📊 5-ASSET CORRELATION HEATMAP</h2>
            <span className="card-tag badge-cyan">LIVE 50-BAR CORR</span>
          </div>

          {displaySyms.length === 0 ? (
            <div className="empty-placeholder">Gathering price series for correlation matrix...</div>
          ) : (
            <div className="table-responsive">
              <table className="heatmap-table">
                <thead>
                  <tr>
                    <th></th>
                    {displaySyms.map((s) => (
                      <th key={s}>{s.replace("USDT", "").replace("USD", "")}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {displaySyms.map((rowSym) => (
                    <tr key={rowSym}>
                      <th>{rowSym.replace("USDT", "").replace("USD", "")}</th>
                      {displaySyms.map((colSym) => {
                        const val =
                          matrix[rowSym] && matrix[rowSym][colSym] !== undefined
                            ? matrix[rowSym][colSym]
                            : rowSym === colSym
                            ? 1.0
                            : 0.0;

                        let cellClass = "cell-neutral";
                        if (rowSym === colSym || val >= 0.5) cellClass = "cell-pos-high";
                        else if (val >= 0.15) cellClass = "cell-pos-mid";
                        else if (val <= -0.5) cellClass = "cell-neg-high";
                        else if (val <= -0.15) cellClass = "cell-neg-mid";

                        const formatted =
                          val === 1
                            ? "1.0"
                            : val >= 0
                            ? `+${Number(val).toFixed(2)}`
                            : Number(val).toFixed(2);

                        return (
                          <td key={colSym} className={`heatmap-cell ${cellClass}`}>
                            {formatted}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
