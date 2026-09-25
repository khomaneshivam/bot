/**
 * QuantAI Terminal - Dedicated Full-Screen "All Trades Ledger"
 * Displays every single open position & historical closed trade with real-time PnL deduction
 */

import React, { useState, useMemo } from "react";
import { useTrading } from "../context/TradingContext";
import { formatCurrency, formatPnL, formatPercent, getPnLColorClass } from "../utils/formatters";

export function AllTradesLedger() {
  const { allTradesData, fetchAllTrades, exportCSV, closePosition } = useTrading();
  const { allTrades, isLoading } = allTradesData;

  const [activeFilter, setActiveFilter] = useState("all"); // "all" | "open" | "wins" | "losses" | "forex" | "crypto"
  const [searchQuery, setSearchQuery] = useState("");

  // Summary Metrics
  const metrics = useMemo(() => {
    const openPos = allTrades.filter((t) => t.is_open);
    const closed = allTrades.filter((t) => !t.is_open);
    const total = allTrades.length;
    const wins = closed.filter((t) => (t.pnl || 0) >= 0).length;
    const losses = closed.filter((t) => (t.pnl || 0) < 0).length;
    const winRate = closed.length > 0 ? ((wins / closed.length) * 100).toFixed(1) : "0.0";
    const netPnl = closed.reduce((acc, t) => acc + (t.pnl || 0), 0);
    const grossProfit = closed.filter((t) => (t.pnl || 0) > 0).reduce((acc, t) => acc + t.pnl, 0);
    const grossLoss = Math.abs(closed.filter((t) => (t.pnl || 0) < 0).reduce((acc, t) => acc + t.pnl, 0));
    const pf = grossLoss > 0 ? (grossProfit / grossLoss).toFixed(2) : grossProfit > 0 ? "MAX" : "1.00";

    return {
      total,
      openCount: openPos.length,
      closedCount: closed.length,
      wins,
      losses,
      winRate,
      netPnl,
      pf,
    };
  }, [allTrades]);

  // Filtered List
  const filteredTrades = useMemo(() => {
    let result = [...allTrades];

    if (activeFilter === "open") {
      result = result.filter((t) => t.is_open);
    } else if (activeFilter === "wins") {
      result = result.filter((t) => !t.is_open && (t.pnl || 0) >= 0);
    } else if (activeFilter === "losses") {
      result = result.filter((t) => !t.is_open && (t.pnl || 0) < 0);
    } else if (activeFilter === "forex") {
      result = result.filter((t) => !(t.symbol || "").includes("USDT"));
    } else if (activeFilter === "crypto") {
      result = result.filter((t) => (t.symbol || "").includes("USDT"));
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter(
        (t) =>
          (t.id && t.id.toLowerCase().includes(q)) ||
          (t.symbol && t.symbol.toLowerCase().includes(q)) ||
          (t.strategy && t.strategy.toLowerCase().includes(q)) ||
          (t.direction && t.direction.toLowerCase().includes(q))
      );
    }

    return result;
  }, [allTrades, activeFilter, searchQuery]);

  return (
    <div className="view-panel active" style={{ display: "block" }}>
      {/* Header */}
      <div className="ledger-view-header">
        <div className="ledger-title-group">
          <h2>
            <span className="header-icon">📜</span> ALL TRADES LEDGER & RISK AUDIT
          </h2>
          <p>
            Exhaustive execution tracking: Active positions, closed trades, real-time balance deductions, and mistake lessons logged to SQLite.
          </p>
        </div>
        <div className="ledger-actions-group">
          <button className="btn-ledger-action" onClick={fetchAllTrades} disabled={isLoading}>
            <span>🔄</span> {isLoading ? "Refreshing..." : "Refresh Ledger"}
          </button>
          <button className="btn-ledger-action btn-export-csv" onClick={exportCSV}>
            <span>📥</span> Export CSV Ledger
          </button>
        </div>
      </div>

      {/* KPI Ribbon */}
      <div className="ledger-kpis-grid">
        <div className="ledger-kpi-card">
          <span className="ledger-kpi-label">Total Portfolio Trades</span>
          <span className="ledger-kpi-val">{metrics.total}</span>
          <span className="ledger-kpi-sub">
            {metrics.openCount} Open · {metrics.closedCount} Closed
          </span>
        </div>

        <div className="ledger-kpi-card">
          <span className="ledger-kpi-label">Win Rate %</span>
          <span className="ledger-kpi-val text-green">{metrics.winRate}%</span>
          <span className="ledger-kpi-sub">
            {metrics.wins} Wins · {metrics.losses} Losses
          </span>
        </div>

        <div className="ledger-kpi-card">
          <span className="ledger-kpi-label">Net Realized PnL</span>
          <span className={`ledger-kpi-val ${getPnLColorClass(metrics.netPnl)}`}>
            {formatPnL(metrics.netPnl)}
          </span>
          <span className="ledger-kpi-sub">Strictly deducted / added to cash balance</span>
        </div>

        <div className="ledger-kpi-card">
          <span className="ledger-kpi-label">Profit Factor</span>
          <span className="ledger-kpi-val text-cyan">{metrics.pf}</span>
          <span className="ledger-kpi-sub">Institutional Quality</span>
        </div>
      </div>

      {/* Filter Tabs & Search Controls */}
      <div className="ledger-controls-bar">
        <div className="ledger-filter-tabs">
          <button
            className={`filter-pill ${activeFilter === "all" ? "active" : ""}`}
            onClick={() => setActiveFilter("all")}
          >
            All Records ({metrics.total})
          </button>
          <button
            className={`filter-pill ${activeFilter === "open" ? "active" : ""}`}
            onClick={() => setActiveFilter("open")}
          >
            🟢 Active Open ({metrics.openCount})
          </button>
          <button
            className={`filter-pill ${activeFilter === "wins" ? "active" : ""}`}
            onClick={() => setActiveFilter("wins")}
          >
            🏆 Profitable Wins ({metrics.wins})
          </button>
          <button
            className={`filter-pill ${activeFilter === "losses" ? "active" : ""}`}
            onClick={() => setActiveFilter("losses")}
          >
            🔴 Losses & Retrained ({metrics.losses})
          </button>
          <button
            className={`filter-pill ${activeFilter === "forex" ? "active" : ""}`}
            onClick={() => setActiveFilter("forex")}
          >
            Forex Pairs
          </button>
          <button
            className={`filter-pill ${activeFilter === "crypto" ? "active" : ""}`}
            onClick={() => setActiveFilter("crypto")}
          >
            Crypto Assets
          </button>
        </div>

        <div className="ledger-search-box">
          <span className="ledger-search-icon">🔍</span>
          <input
            type="text"
            className="ledger-search-input"
            placeholder="Search Symbol, ID, Strategy..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Exhaustive Trades Table */}
      <div className="glass-panel data-card full-width">
        <div className="table-responsive">
          <table className="quant-table">
            <thead>
              <tr>
                <th>Status</th>
                <th>Trade ID</th>
                <th>Symbol</th>
                <th>Type</th>
                <th>Size / Lots</th>
                <th>Entry Price</th>
                <th>Exit Price</th>
                <th>SL / TP</th>
                <th>PnL ($)</th>
                <th>Return %</th>
                <th>Strategy</th>
                <th>Exit / Retrain Cause</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredTrades.length === 0 ? (
                <tr>
                  <td colSpan="13" className="text-center text-muted">
                    No trades match the selected filter criteria.
                  </td>
                </tr>
              ) : (
                filteredTrades.map((t) => {
                  const isOpen = t.is_open;
                  const pnl = isOpen ? t.unrealized_pnl || 0 : t.pnl || 0;
                  const retPct = t.return_pct || 0;
                  const isCrypto = (t.symbol || "").includes("USDT");

                  return (
                    <tr key={t.id}>
                      <td>
                        {isOpen ? (
                          <span className="status-pill-open">
                            <span className="status-pulse-dot" style={{ width: 6, height: 6 }}></span>
                            ACTIVE
                          </span>
                        ) : pnl >= 0 ? (
                          <span className="status-pill-win">WIN</span>
                        ) : (
                          <span className="status-pill-loss">LOSS</span>
                        )}
                      </td>
                      <td>
                        <strong>#{t.id}</strong>
                      </td>
                      <td>
                        <strong>{t.symbol}</strong>
                        <span className="metric-badge" style={{ fontSize: "0.55rem", marginLeft: 4 }}>
                          {isCrypto ? "CRYPTO" : "FOREX"}
                        </span>
                      </td>
                      <td>
                        <span className={t.direction === "BUY" ? "tag-buy" : "tag-sell"}>
                          {t.direction}
                        </span>
                      </td>
                      <td>{t.size}</td>
                      <td>${Number(t.entry_price || 0).toFixed(4)}</td>
                      <td>
                        $
                        {Number(
                          isOpen ? t.current_price || t.entry_price : t.close_price || t.current_price
                        ).toFixed(4)}
                      </td>
                      <td style={{ fontSize: "0.75rem" }}>
                        SL: {t.sl || "-"} / TP: {t.tp || "-"}
                      </td>
                      <td className={getPnLColorClass(pnl)}>
                        <strong>{formatPnL(pnl)}</strong>
                      </td>
                      <td className={getPnLColorClass(retPct)}>{formatPercent(retPct)}</td>
                      <td>
                        <span className="metric-badge" style={{ fontSize: "0.65rem" }}>
                          {t.strategy || "Ensemble"}
                        </span>
                      </td>
                      <td>
                        {!isOpen && pnl < 0 ? (
                          <span
                            className="mistake-lesson-badge"
                            title={t.loss_cause || "Pattern penalized in vector shield"}
                          >
                            {t.loss_cause || "Cosine Shield Active"}
                          </span>
                        ) : (
                          <span className="text-muted">
                            {t.exit_reason || (isOpen ? "In Progress" : "COMPLETE")}
                          </span>
                        )}
                      </td>
                      <td>
                        {isOpen ? (
                          <button
                            className="btn-close-pos"
                            onClick={() => closePosition(t.id)}
                            title="Manually liquidate position"
                          >
                            Close
                          </button>
                        ) : (
                          <span className="text-muted" style={{ fontSize: "0.72rem" }}>
                            {t.close_time ? t.close_time.slice(11, 19) : "Archived"}
                          </span>
                        )}
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
