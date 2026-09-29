import React, { useState } from "react";
import { useTrading } from "../../context/TradingContext";
import { StatusBadge } from "../../components/common/StatusBadge";
import { EmptyState } from "../../components/common/EmptyState";
import { History, RefreshCw, Filter, Search, ShieldCheck, AlertCircle } from "lucide-react";

export function AuditTimelineView() {
  const { auditLogsData, fetchAuditLogs } = useTrading();
  const { events, isLoading } = auditLogsData;

  const [searchQuery, setSearchQuery] = useState("");
  const [filterAction, setFilterAction] = useState("ALL");
  const [filterResult, setFilterResult] = useState("ALL");

  const filteredEvents = (events || []).filter((ev) => {
    if (filterAction !== "ALL" && !String(ev.action).includes(filterAction)) return false;
    if (filterResult !== "ALL" && ev.result !== filterResult) return false;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      return (
        String(ev.action).toLowerCase().includes(q) ||
        String(ev.target).toLowerCase().includes(q) ||
        String(ev.actor_id).toLowerCase().includes(q) ||
        String(ev.actor_role).toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 select-none bg-slate-950">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-800">
        <div>
          <h1 className="text-base font-bold font-mono text-white tracking-wide flex items-center gap-2">
            <History className="w-4 h-4 text-sky-400" />
            <span>IMMUTABLE OPERATIONAL AUDIT LOG & COMPLIANCE TRAIL</span>
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            Chronological journal of every privileged action, risk evaluation, execution event, and mode transition.
          </p>
        </div>

        <button
          onClick={fetchAuditLogs}
          disabled={isLoading}
          className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700 text-xs font-mono font-medium flex items-center gap-1.5 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
          <span>Refresh Audit</span>
        </button>
      </div>

      {/* Filter & Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono">
        <div className="flex flex-wrap items-center gap-2">
          {/* Search Input */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2 text-slate-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter by actor, action, target..."
              className="pl-8 pr-3 py-1 bg-slate-950 border border-slate-700 rounded-md text-white font-mono focus:outline-none focus:border-sky-500 w-56"
            />
          </div>

          {/* Action Filter */}
          <select
            value={filterAction}
            onChange={(e) => setFilterAction(e.target.value)}
            className="bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-300 focus:outline-none"
          >
            <option value="ALL">All Actions</option>
            <option value="ORDER">Orders & Fills</option>
            <option value="MODE">Mode Changes</option>
            <option value="BOT">Bot Controls</option>
            <option value="RESET">Resets</option>
            <option value="LOGIN">Authentication</option>
            <option value="CIRCUIT">Circuit Breakers</option>
          </select>

          {/* Result Filter */}
          <select
            value={filterResult}
            onChange={(e) => setFilterResult(e.target.value)}
            className="bg-slate-950 border border-slate-700 rounded px-2 py-1 text-slate-300 focus:outline-none"
          >
            <option value="ALL">All Results</option>
            <option value="SUCCESS">Success</option>
            <option value="FAILURE">Failure</option>
            <option value="DISCREPANCY">Discrepancy</option>
          </select>
        </div>

        <div className="text-slate-400">
          Showing {filteredEvents.length} chronological events
        </div>
      </div>

      {/* Audit Log Table */}
      <div className="rounded-lg border border-slate-800 bg-slate-900 overflow-hidden shadow-lg">
        <div className="overflow-x-auto">
          <table className="terminal-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Event ID</th>
                <th>Actor / Role</th>
                <th>Action</th>
                <th>Target</th>
                <th>Result</th>
                <th>Details / Value</th>
                <th>IP Address</th>
              </tr>
            </thead>
            <tbody>
              {filteredEvents.length === 0 ? (
                <tr>
                  <td colSpan="8" className="py-8 text-center">
                    <EmptyState
                      title="No Audit Events Found"
                      description="No audit events matched your filter criteria."
                    />
                  </td>
                </tr>
              ) : (
                filteredEvents.map((ev, i) => {
                  const isSuccess = ev.result === "SUCCESS";
                  return (
                    <tr key={ev.event_id || i} className="hover:bg-slate-850 transition-colors">
                      <td className="font-mono text-slate-400 text-[11px] whitespace-nowrap">
                        {ev.timestamp}
                      </td>
                      <td className="font-mono text-slate-500 text-[10px]">
                        {ev.event_id}
                      </td>
                      <td>
                        <div className="font-mono font-bold text-slate-200">
                          {ev.actor_id}
                        </div>
                        <div className="text-[10px] font-mono text-sky-400 uppercase">
                          {ev.actor_role}
                        </div>
                      </td>
                      <td className="font-mono font-bold text-white text-xs">
                        {ev.action}
                      </td>
                      <td className="font-mono text-slate-300">
                        {ev.target}
                      </td>
                      <td>
                        <StatusBadge
                          status={isSuccess ? "HEALTHY" : "DANGER"}
                          label={ev.result}
                          size="sm"
                        />
                      </td>
                      <td className="font-mono text-slate-400 text-[11px] max-w-xs truncate">
                        {ev.new_val || ev.old_val ? `${ev.old_val ? `${ev.old_val} → ` : ""}${ev.new_val || ""}` : "Completed"}
                      </td>
                      <td className="font-mono text-slate-500 text-[10px]">
                        {ev.client_ip || "127.0.0.1"}
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
