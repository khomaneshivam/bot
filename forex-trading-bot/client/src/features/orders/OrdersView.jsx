import React, { useState } from "react";
import { useTrading } from "../../context/TradingContext";
import { StatusBadge } from "../../components/common/StatusBadge";
import { EmptyState } from "../../components/common/EmptyState";
import { formatPrice, formatTimestamp } from "../../utils/formatters";
import { ORDER_STATUSES } from "../../utils/constants";
import { FileText, RefreshCw, AlertOctagon, CheckCircle2, Clock, ArrowRight } from "lucide-react";

export function OrdersView() {
  const { ordersData, fetchOrders } = useTrading();
  const { orders, transitions, isLoading } = ordersData;

  const [selectedOrder, setSelectedOrder] = useState(null);

  const activeSelected = selectedOrder
    ? orders.find((o) => o.id === selectedOrder) || orders[0]
    : orders[0];

  const orderTransitions = activeSelected
    ? (transitions || []).filter((t) => t.order_id === activeSelected.id)
    : [];

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 select-none bg-slate-950">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-800">
        <div>
          <h1 className="text-base font-bold font-mono text-white tracking-wide flex items-center gap-2">
            <FileText className="w-4 h-4 text-sky-400" />
            <span>ORDER STATE MACHINE & AUDIT LIFECYCLE</span>
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            Deterministic state transitions: CREATED → RISK APPROVED → SUBMITTED → ACKNOWLEDGED → FILLED.
          </p>
        </div>

        <button
          onClick={fetchOrders}
          disabled={isLoading}
          className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700 text-xs font-mono font-medium flex items-center gap-1.5 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
          <span>Refresh Orders</span>
        </button>
      </div>

      {/* Selected Order Stepper Timeline */}
      {activeSelected && (
        <div className="p-4 rounded-lg bg-slate-900 border border-slate-800 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-800/80">
            <div className="flex items-center gap-2 text-xs font-mono">
              <span className="text-slate-400">Inspecting Order:</span>
              <span className="text-white font-bold">{activeSelected.id}</span>
              <span className="text-slate-500">({activeSelected.client_order_id})</span>
            </div>
            <StatusBadge status={activeSelected.status} />
          </div>

          {/* Stepper Progress */}
          {activeSelected.status === "UNKNOWN" || activeSelected.status === "RECONCILIATION_REQUIRED" ? (
            <div className="p-3 rounded-lg bg-rose-500/15 border border-rose-500/40 text-rose-300 flex items-center gap-3">
              <AlertOctagon className="w-6 h-6 text-rose-400 shrink-0 animate-bounce" />
              <div>
                <div className="font-mono font-black text-xs uppercase tracking-wide">
                  CRITICAL: ORDER IN {activeSelected.status} STATE
                </div>
                <div className="text-[11px] font-mono text-slate-300 mt-0.5">
                  This order has not confirmed execution with the broker. It must NOT be treated as FILLED. Broker reconciliation audit required.
                </div>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-6 gap-2 text-[10px] font-mono">
              {[
                { key: "CREATED", label: "1. CREATED" },
                { key: "RISK_APPROVED", label: "2. RISK APPROVED" },
                { key: "SUBMITTED", label: "3. SUBMITTED" },
                { key: "ACKNOWLEDGED", label: "4. ACKNOWLEDGED" },
                { key: "PARTIALLY_FILLED", label: "5. PARTIAL FILL" },
                { key: "FILLED", label: "6. FILLED" },
              ].map((step, idx) => {
                const currentStatus = activeSelected.status;
                const isFailed = currentStatus === "REJECTED" || currentStatus === "CANCELLED";
                const isPassed =
                  currentStatus === "FILLED" ||
                  (currentStatus === step.key) ||
                  (idx === 0 && currentStatus !== "CREATED");

                return (
                  <div
                    key={step.key}
                    className={`p-2 rounded border text-center transition-all ${
                      currentStatus === step.key
                        ? "bg-sky-500/20 text-sky-300 border-sky-500/50 font-bold shadow-sm"
                        : isPassed
                        ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                        : "bg-slate-950/60 text-slate-600 border-slate-800"
                    }`}
                  >
                    <div>{step.label}</div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Transition History log for this order */}
          {orderTransitions.length > 0 && (
            <div className="pt-2 border-t border-slate-800/80">
              <span className="text-[10px] font-mono uppercase text-slate-500 tracking-wider block mb-1">
                State Transitions Journal:
              </span>
              <div className="space-y-1 max-h-28 overflow-y-auto">
                {orderTransitions.map((tr, i) => (
                  <div key={i} className="text-[11px] font-mono text-slate-400 flex items-center gap-2">
                    <span className="text-slate-500">{tr.timestamp}</span>
                    <span className="text-sky-400 font-bold">{tr.from_status} → {tr.to_status}</span>
                    <span className="text-slate-300">({tr.reason || "Automatic state transition"})</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Orders Table */}
      <div className="rounded-lg border border-slate-800 bg-slate-900 overflow-hidden shadow-lg">
        <div className="overflow-x-auto">
          <table className="terminal-table">
            <thead>
              <tr>
                <th>Order ID</th>
                <th>Client Order ID</th>
                <th>Broker Order ID</th>
                <th>Symbol</th>
                <th>Side</th>
                <th>Qty</th>
                <th>Intended Price</th>
                <th>Executed Price</th>
                <th>Slippage</th>
                <th>Status</th>
                <th>Created At</th>
              </tr>
            </thead>
            <tbody>
              {orders.length === 0 ? (
                <tr>
                  <td colSpan="11" className="py-8 text-center">
                    <EmptyState
                      title="No Orders Found"
                      description="No orders have been submitted in the current operational session."
                    />
                  </td>
                </tr>
              ) : (
                orders.map((ord) => {
                  const isSelected = activeSelected && activeSelected.id === ord.id;
                  const isBuy = (ord.side || "BUY").toUpperCase() === "BUY";
                  const slippage = ord.executed_price && ord.intended_price
                    ? (Number(ord.executed_price) - Number(ord.intended_price)).toFixed(5)
                    : "--";

                  return (
                    <tr
                      key={ord.id}
                      onClick={() => setSelectedOrder(ord.id)}
                      tabIndex={0}
                      role="button"
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          setSelectedOrder(ord.id);
                        }
                      }}
                      className={`cursor-pointer transition-colors focus:outline-none focus:bg-slate-800 ${
                        isSelected ? "bg-slate-800" : "hover:bg-slate-850"
                      }`}
                    >
                      <td className="font-mono font-bold text-sky-400">
                        {ord.id}
                      </td>
                      <td className="font-mono text-slate-400 text-[11px]">
                        {ord.client_order_id}
                      </td>
                      <td className="font-mono text-slate-300 text-[11px]">
                        {ord.broker_order_id || "Unassigned"}
                      </td>
                      <td className="font-mono font-bold text-white">
                        {ord.symbol}
                      </td>
                      <td>
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-bold ${
                            isBuy
                              ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                              : "bg-rose-500/15 text-rose-400 border border-rose-500/30"
                          }`}
                        >
                          {ord.side}
                        </span>
                      </td>
                      <td className="font-mono tabular-nums text-slate-200">
                        {ord.quantity}
                      </td>
                      <td className="font-mono tabular-nums text-slate-200">
                        {formatPrice(ord.intended_price, ord.symbol)}
                      </td>
                      <td className="font-mono tabular-nums text-slate-200">
                        {ord.executed_price ? formatPrice(ord.executed_price, ord.symbol) : "--"}
                      </td>
                      <td className="font-mono tabular-nums text-slate-400 text-[11px]">
                        {slippage}
                      </td>
                      <td>
                        <StatusBadge status={ord.status} size="sm" />
                      </td>
                      <td className="font-mono text-slate-400 text-[11px]">
                        {formatTimestamp(ord.created_at)}
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
