/**
 * QuantAI Terminal - AI Adaptive Learning & Mistake Retraining Studio
 */

import React, { useState, useEffect } from "react";
import { useTrading } from "../context/TradingContext";
import { api } from "../services/api";

export function AIStudioView() {
  const { telemetry } = useTrading();
  const { ml_stats } = telemetry;
  const [wrongTrades, setWrongTrades] = useState([]);
  const [isRetraining, setIsRetraining] = useState(false);

  useEffect(() => {
    api.getWrongTrades()
      .then((data) => {
        if (data && data.wrong_trades) {
          setWrongTrades(data.wrong_trades);
        }
      })
      .catch((err) => console.error("Error loading wrong trades:", err));
  }, []);

  const handleRetrain = async () => {
    setIsRetraining(true);
    try {
      const res = await api.triggerRetrain();
      alert(`Neural Retrain Complete: ${res.message || "Model weights updated"}`);
    } catch (err) {
      console.error("Retrain error:", err);
    } finally {
      setIsRetraining(false);
    }
  };

  return (
    <div className="view-panel active" style={{ display: "block" }}>
      <div className="ledger-view-header">
        <div className="ledger-title-group">
          <h2>
            <span className="header-icon">🧠</span> AI ADAPTIVE LEARNING & MISTAKE RETRAINING STUDIO
          </h2>
          <p>
            Continuous online gradient adaptation, Cosine Negative Pattern Shield, and Gemini neural veto reasoning telemetry.
          </p>
        </div>
        <div className="ledger-actions-group">
          <button className="btn-ledger-action" onClick={handleRetrain} disabled={isRetraining}>
            <span>⚡</span> {isRetraining ? "Retraining Weights..." : "Trigger Neural Retraining"}
          </button>
        </div>
      </div>

      <div className="grid-2col" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 24 }}>
        {/* Cosine Shield Box */}
        <div className="glass-panel data-card">
          <div className="card-header">
            <h2 className="card-title">🛡️ COSINE NEGATIVE PATTERN SHIELD</h2>
            <span className="card-tag badge-cyan">
              {ml_stats ? ml_stats.vetoed_trades_count || 0 : 0} VETOES
            </span>
          </div>
          <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: 12 }}>
            The system vectorizes every trade at entry into a 60-dimensional quantitative snapshot. Whenever a trade results in a loss, its normalized feature vector is memorized. Future setups with Cosine Similarity &gt; 0.88 to past losses are strictly vetoed.
          </p>

          <div className="terminal-log-feed" style={{ maxHeight: 280 }}>
            {wrongTrades.length === 0 ? (
              <div className="log-entry log-info">
                <span className="log-time">[ACTIVE]</span> Cosine Shield active. Monitoring candidate setups. Zero negative clusters recorded.
              </div>
            ) : (
              wrongTrades.map((wt, i) => (
                <div className="log-entry" key={i}>
                  <span className="log-time">[{wt.time ? wt.time.slice(11, 19) : "LOG"}]</span>
                  <span className="log-tag tag-negative-shield">[SHIELDED]</span>
                  <span className="log-msg">
                    #{wt.id} {wt.direction} {wt.symbol} - Lesson: {wt.loss_cause || "Loss pattern vector memorized"}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Gemini AI Quant Hybrid Box */}
        <div className="glass-panel data-card">
          <div className="card-header">
            <h2 className="card-title">🤖 GEMINI HYBRID QUANT LOGIC</h2>
            <span className="card-tag badge-emerald">ACTIVE</span>
          </div>
          <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: 12 }}>
            Combines low-latency local technical ensembles (Trend Momentum, RSI Mean Reversion, Keltner Breakout, SMC Order Blocks, DXY Macro) with Google Gemini AI structured market regime synthesis and sentiment audits.
          </p>

          <div
            className="ai-box"
            style={{
              padding: 14,
              background: "var(--bg-card-subtle)",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border-subtle)",
              marginBottom: 16,
            }}
          >
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 6 }}>
              CURRENT ML STATUS:
            </div>
            <div style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--color-green)" }}>
              ONLINE &amp; ADAPTING ({(ml_stats ? ml_stats.parameters_count || 45000 : 45000).toLocaleString()} weights)
            </div>
          </div>

          <div
            className="ai-box"
            style={{
              padding: 14,
              background: "var(--bg-card-subtle)",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 6 }}>
              VETO SAFEGUARD SUMMARY:
            </div>
            <div style={{ fontSize: "0.85rem", color: "var(--text-primary)" }}>
              {ml_stats ? ml_stats.last_veto_reason || "All risk filters operating normally. No high-risk anomalies detected." : "Normal operations"}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
