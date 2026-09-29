import React from "react";
import { useTrading } from "../../context/TradingContext";
import { StatusBadge } from "../../components/common/StatusBadge";
import { Scale, RefreshCw, AlertOctagon, CheckCircle2, ShieldAlert } from "lucide-react";

export function ReconcileView() {
  const { reconciliationData, fetchReconciliation, openConfirmModal } = useTrading();
  const { report, has_active_mismatch, internal_positions, broker_positions, isLoading } = reconciliationData;

  const discrepancies = report?.discrepancies || [];
  const isHalted = has_active_mismatch || discrepancies.length > 0;

  // Build unified comparison map
  const symbolMap = {};

  (internal_positions || []).forEach((pos) => {
    symbolMap[pos.symbol] = {
      symbol: pos.symbol,
      internal: `${pos.direction || pos.side} ${pos.size}`,
      broker: "NONE",
      diff: `${pos.size} internal surplus`,
      status: "MISMATCH",
      details: "Missing broker confirmation",
    };
  });

  (broker_positions || []).forEach((bPos) => {
    const sym = bPos.symbol;
    const bStr = `${bPos.side} ${bPos.quantity || bPos.size}`;
    if (symbolMap[sym]) {
      const match = symbolMap[sym].internal === bStr;
      symbolMap[sym].broker = bStr;
      symbolMap[sym].diff = match ? "0.00" : "Volume/Side Mismatch";
      symbolMap[sym].status = match ? "MATCH" : "MISMATCH";
      symbolMap[sym].details = match ? "Reconciled with broker gateway" : "Volume discrepancy detected";
    } else {
      symbolMap[sym] = {
        symbol: sym,
        internal: "NONE",
        broker: bStr,
        diff: `${bPos.quantity || bPos.size} broker orphan`,
        status: "MISMATCH",
        details: "Orphan broker position without internal ticket",
      };
    }
  });

  const reconciliationRows = Object.values(symbolMap);

  const handleManualReconcile = () => {
    openConfirmModal({
      title: "TRIGGER BROKER RECONCILIATION AUDIT",
      description: "Queries the broker gateway directly to cross-verify all internal active positions with authoritative broker state.",
      confirmVariant: "primary",
      confirmLabel: "Run Audit",
      action: async () => {
        await fetchReconciliation();
      },
    });
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6 select-none bg-slate-950">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-800">
        <div>
          <h1 className="text-base font-bold font-mono text-white tracking-wide flex items-center gap-2">
            <Scale className="w-4 h-4 text-sky-400" />
            <span>INDEPENDENT BROKER RECONCILIATION CONSOLE</span>
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            Automated discrepancy detector: Compares internal application state against authoritative broker tickets.
          </p>
        </div>

        <button
          onClick={handleManualReconcile}
          disabled={isLoading}
          className="px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-mono font-bold flex items-center gap-1.5 transition-colors shadow-sm"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
          <span>Audit Broker State</span>
        </button>
      </div>

      {/* UNMISSABLE EMERGENCY HALT BANNER IF MISMATCH DETECTED */}
      {isHalted ? (
        <div className="p-4 rounded-xl bg-rose-600/25 border-2 border-rose-500 text-rose-100 flex items-center gap-4 shadow-2xl animate-pulse">
          <div className="p-3 rounded-lg bg-rose-600 text-white shrink-0">
            <AlertOctagon className="w-8 h-8" />
          </div>
          <div>
            <div className="text-lg font-black font-mono tracking-wider text-rose-200">
              🚨 NEW TRADES HALTED · CRITICAL BROKER MISMATCH DETECTED
            </div>
            <div className="text-xs font-mono text-slate-200 mt-1">
              Internal active positions differ from authoritative broker truth. To prevent catastrophic unhedged risk, all autonomous order submissions are strictly halted.
            </div>
          </div>
        </div>
      ) : (
        <div className="p-3.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 flex items-center gap-3 font-mono text-xs">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          <div>
            <strong className="text-emerald-200 uppercase">State Synchronized:</strong> Internal memory ledger matches broker positions exactly. Zero discrepancies detected.
          </div>
        </div>
      )}

      {/* Reconciliation Comparison Table */}
      <div className="rounded-lg border border-slate-800 bg-slate-900 overflow-hidden shadow-lg">
        <div className="p-3.5 border-b border-slate-800/80 flex justify-between items-center">
          <span className="text-xs font-mono font-bold uppercase text-white tracking-wider">
            Internal vs Broker Position Audit Matrix
          </span>
          <span className="text-[11px] font-mono text-slate-400">
            Checked: {report?.timestamp || "Boot Recovery Check"}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="terminal-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Internal Position</th>
                <th>Authoritative Broker Position</th>
                <th>Difference / Variance</th>
                <th>Reconciliation Status</th>
                <th>Audit Details</th>
              </tr>
            </thead>
            <tbody>
              {reconciliationRows.length === 0 ? (
                <tr>
                  <td colSpan="6" className="py-8 text-center font-mono text-xs text-slate-400">
                    No active positions open in internal database or broker account. Both states idle and synchronized.
                  </td>
                </tr>
              ) : (
                reconciliationRows.map((row) => {
                  const isMatch = row.status === "MATCH";
                  return (
                    <tr
                      key={row.symbol}
                      className={!isMatch ? "bg-rose-950/30 hover:bg-rose-950/50" : "hover:bg-slate-850"}
                    >
                      <td className="font-mono font-bold text-white text-xs">
                        {row.symbol}
                      </td>
                      <td className="font-mono text-slate-200">
                        {row.internal}
                      </td>
                      <td className="font-mono text-sky-400 font-bold">
                        {row.broker}
                      </td>
                      <td className={`font-mono font-bold ${isMatch ? "text-slate-400" : "text-rose-400"}`}>
                        {row.diff}
                      </td>
                      <td>
                        <StatusBadge
                          status={row.status}
                          label={row.status === "MATCH" ? "MATCH" : "CRITICAL MISMATCH"}
                          size="sm"
                        />
                      </td>
                      <td className="font-mono text-slate-400 text-[11px]">
                        {row.details}
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
