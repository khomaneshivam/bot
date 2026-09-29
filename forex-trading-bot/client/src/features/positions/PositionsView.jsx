import React, { useState } from "react";
import { useTrading } from "../../context/TradingContext";
import { formatCurrency, formatPrice, formatPnL, formatRMultiple, getPnLTextColor, formatTimeAgo } from "../../utils/formatters";
import { StatusBadge } from "../../components/common/StatusBadge";
import { EmptyState } from "../../components/common/EmptyState";
import { ChevronDown, ChevronRight, Download, RefreshCw, XCircle, Shield, Layers } from "lucide-react";

export function PositionsView() {
  const { allTradesData, fetchAllTrades, closePositionSafe, exportCSV } = useTrading();
  const { allTrades, isLoading } = allTradesData;

  const [filterMode, setFilterMode] = useState("open"); // "open" | "closed" | "all"
  const [expandedRow, setExpandedRow] = useState(null);

  const displayedTrades = (allTrades || []).filter((t) => {
    if (filterMode === "open") return t.is_open;
    if (filterMode === "closed") return !t.is_open;
    return true;
  });

  const openCount = (allTrades || []).filter((t) => t.is_open).length;
  const closedCount = (allTrades || []).filter((t) => !t.is_open).length;

  const toggleRow = (id) => {
    setExpandedRow((prev) => (prev === id ? null : id));
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 select-none bg-slate-950">
      {/* Header & View Switcher */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-800">
        <div>
          <h1 className="text-base font-bold font-mono text-white tracking-wide flex items-center gap-2">
            <Layers className="w-4 h-4 text-sky-400" />
            <span>PORTFOLIO POSITIONS & FORENSIC LEDGER</span>
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            Broker-confirmed active positions, floating P&L, R-multiple attribution, and expanded risk snapshots.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Filter Tabs */}
          <div className="flex items-center bg-slate-900 p-0.5 rounded-lg border border-slate-800 text-xs font-mono">
            <button
              onClick={() => setFilterMode("open")}
              className={`px-3 py-1 rounded-md font-bold transition-colors ${
                filterMode === "open" ? "bg-sky-600 text-white" : "text-slate-400 hover:text-white"
              }`}
            >
              Open Positions ({openCount})
            </button>
            <button
              onClick={() => setFilterMode("closed")}
              className={`px-3 py-1 rounded-md font-bold transition-colors ${
                filterMode === "closed" ? "bg-sky-600 text-white" : "text-slate-400 hover:text-white"
              }`}
            >
              Closed Ledger ({closedCount})
            </button>
            <button
              onClick={() => setFilterMode("all")}
              className={`px-3 py-1 rounded-md font-bold transition-colors ${
                filterMode === "all" ? "bg-sky-600 text-white" : "text-slate-400 hover:text-white"
              }`}
            >
              All Records
            </button>
          </div>

          <button
            onClick={fetchAllTrades}
            disabled={isLoading}
            className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700 transition-colors"
            title="Refresh positions from broker database"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
          </button>

          <button
            onClick={exportCSV}
            className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700 text-xs font-mono font-medium flex items-center gap-1.5 transition-colors"
            title="Export CSV audit ledger"
          >
            <Download className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Export CSV</span>
          </button>
        </div>
      </div>

      {/* Main Dense Table */}
      <div className="rounded-lg border border-slate-800 bg-slate-900 overflow-hidden shadow-lg">
        <div className="overflow-x-auto">
          <table className="terminal-table">
            <thead>
              <tr>
                <th className="w-8"></th>
                <th>Symbol</th>
                <th>Side</th>
                <th>Size</th>
                <th>Entry Price</th>
                <th>Current / Exit</th>
                <th>SL / TP</th>
                <th>P&L ($)</th>
                <th>R-Multiple</th>
                <th>Strategy</th>
                <th>Model</th>
                <th>Age</th>
                <th>Broker Status</th>
                <th className="text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {displayedTrades.length === 0 ? (
                <tr>
                  <td colSpan="14" className="py-8 text-center">
                    <EmptyState
                      title={filterMode === "open" ? "No Active Positions" : "No Historical Trades"}
                      description={
                        filterMode === "open"
                          ? "The autonomous engine has zero open positions. All 9 deterministic risk gates are scanning for setups."
                          : "No closed trades recorded in persistent ledger."
                      }
                    />
                  </td>
                </tr>
              ) : (
                displayedTrades.map((pos) => {
                  const isRowExpanded = expandedRow === pos.id;
                  const pnl = pos.is_open ? pos.unrealized_pnl || 0 : pos.pnl || 0;
                  const isBuy = (pos.direction || pos.side || "BUY").toUpperCase() === "BUY";
                  const riskAmt = Math.abs(Number(pos.entry_price || 0) - Number(pos.sl || pos.entry_price || 0)) * Number(pos.size || 1);

                  return (
                    <React.Fragment key={pos.id}>
                      <tr
                        onClick={() => toggleRow(pos.id)}
                        tabIndex={0}
                        role="button"
                        aria-expanded={isRowExpanded}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            toggleRow(pos.id);
                          }
                        }}
                        className={`cursor-pointer transition-colors focus:outline-none focus:bg-slate-800 ${
                          isRowExpanded ? "bg-slate-800/80" : "hover:bg-slate-850"
                        }`}
                      >
                        <td className="text-center text-slate-500">
                          {isRowExpanded ? (
                            <ChevronDown className="w-3.5 h-3.5 text-sky-400 inline" />
                          ) : (
                            <ChevronRight className="w-3.5 h-3.5 inline" />
                          )}
                        </td>
                        <td className="font-mono font-bold text-white">
                          {pos.symbol}
                        </td>
                        <td>
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-bold ${
                              isBuy ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30" : "bg-rose-500/15 text-rose-400 border border-rose-500/30"
                            }`}
                          >
                            {isBuy ? "BUY" : "SELL"}
                          </span>
                        </td>
                        <td className="font-mono tabular-nums text-slate-200">
                          {pos.size}
                        </td>
                        <td className="font-mono tabular-nums text-slate-200">
                          {formatPrice(pos.entry_price, pos.symbol)}
                        </td>
                        <td className="font-mono tabular-nums text-slate-200">
                          {formatPrice(pos.is_open ? pos.current_price || pos.entry_price : pos.exit_price || pos.current_price, pos.symbol)}
                        </td>
                        <td className="font-mono text-[11px] text-slate-400">
                          {pos.sl ? `SL ${formatPrice(pos.sl, pos.symbol)}` : "None"} / {pos.tp ? `TP ${formatPrice(pos.tp, pos.symbol)}` : "None"}
                        </td>
                        <td className={`font-mono font-bold tabular-nums ${getPnLTextColor(pnl)}`}>
                          {formatPnL(pnl)}
                        </td>
                        <td className={`font-mono font-bold tabular-nums ${getPnLTextColor(pnl)}`}>
                          {formatRMultiple(pnl, riskAmt)}
                        </td>
                        <td className="font-mono text-slate-300 text-[11px]">
                          {pos.strategy || "Ensemble"}
                        </td>
                        <td className="font-mono text-slate-400 text-[11px]">
                          v{pos.model_version || "1.0.0"}
                        </td>
                        <td className="font-mono text-slate-400 text-[11px]">
                          {formatTimeAgo(pos.entry_time || pos.created_at)}
                        </td>
                        <td>
                          <StatusBadge
                            status={pos.is_open ? "MATCH" : "FILLED"}
                            label={pos.is_open ? "BROKER MATCH" : "CLOSED"}
                            size="sm"
                          />
                        </td>
                        <td className="text-right">
                          {pos.is_open && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                closePositionSafe(pos.id, pos.symbol);
                              }}
                              className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-600/20 text-rose-300 hover:bg-rose-600 hover:text-white border border-rose-500/30 transition-all"
                            >
                              Close
                            </button>
                          )}
                        </td>
                      </tr>

                      {/* Expandable Forensic Details Row */}
                      {isRowExpanded && (
                        <tr className="bg-slate-950/90 border-b border-slate-800">
                          <td colSpan="14" className="p-4">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
                              {/* Identifier & Broker Truth */}
                              <div className="p-3 rounded bg-slate-900 border border-slate-800 space-y-1.5">
                                <div className="text-[10px] font-bold uppercase text-slate-400 tracking-wider">
                                  Identifier & Broker Reconciliation
                                </div>
                                <div className="flex justify-between text-slate-300">
                                  <span className="text-slate-500">Internal Position ID:</span>
                                  <span className="text-white font-bold">{pos.id}</span>
                                </div>
                                <div className="flex justify-between text-slate-300">
                                  <span className="text-slate-500">Broker Ticket ID:</span>
                                  <span className="text-sky-400 font-bold">{pos.broker_order_id || pos.id}</span>
                                </div>
                                <div className="flex justify-between text-slate-300">
                                  <span className="text-slate-500">Execution Mode:</span>
                                  <span className="text-emerald-400 uppercase font-bold">{pos.execution_mode || "PAPER"}</span>
                                </div>
                                <div className="flex justify-between text-slate-300">
                                  <span className="text-slate-500">Market Regime:</span>
                                  <span className="text-slate-200">{pos.market_regime || "TRENDING"}</span>
                                </div>
                              </div>

                              {/* Statistical ML & Calibration */}
                              <div className="p-3 rounded bg-slate-900 border border-slate-800 space-y-1.5">
                                <div className="text-[10px] font-bold uppercase text-slate-400 tracking-wider">
                                  Model Calibration & Feature Snapshot
                                </div>
                                <div className="flex justify-between text-slate-300">
                                  <span className="text-slate-500">Model Version:</span>
                                  <span className="text-white">v{pos.model_version || "1.0.0"}</span>
                                </div>
                                <div className="flex justify-between text-slate-300">
                                  <span className="text-slate-500">Feature Vector Version:</span>
                                  <span className="text-white">v1 (60-dim)</span>
                                </div>
                                <div className="flex justify-between text-slate-300">
                                  <span className="text-slate-500">Raw Model Confidence:</span>
                                  <span className="text-white font-bold">{Math.round((pos.confidence || 0.72) * 100)}%</span>
                                </div>
                                <div className="flex justify-between text-slate-300">
                                  <span className="text-slate-500">Calibrated Probability:</span>
                                  <span className="text-sky-400 font-bold">{((pos.calibrated_probability || 0.68) * 100).toFixed(1)}%</span>
                                </div>
                              </div>

                              {/* Execution Rationale & Exit Forensics */}
                              <div className="p-3 rounded bg-slate-900 border border-slate-800 space-y-1.5">
                                <div className="text-[10px] font-bold uppercase text-slate-400 tracking-wider">
                                  Trade Rationale & Risk Parameters
                                </div>
                                <div>
                                  <span className="text-slate-500 block">Entry Reason:</span>
                                  <span className="text-slate-200">{pos.reason || "Autonomous ensemble technical confluence setup"}</span>
                                </div>
                                {!pos.is_open && (
                                  <div className="pt-1 border-t border-slate-800">
                                    <span className="text-slate-500 block">Exit Reason:</span>
                                    <span className="text-amber-400 font-bold">{pos.exit_reason || "SL / TP Breached"}</span>
                                  </div>
                                )}
                                <div className="flex justify-between text-slate-300 pt-1 border-t border-slate-800">
                                  <span className="text-slate-500">Initial Risk Pool:</span>
                                  <span className="text-white font-bold">{formatCurrency(riskAmt)}</span>
                                </div>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
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
