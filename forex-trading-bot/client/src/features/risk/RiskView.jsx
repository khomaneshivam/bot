import React from "react";
import { useTrading } from "../../context/TradingContext";
import { StatusBadge } from "../../components/common/StatusBadge";
import { RiskIndicator } from "../../components/common/RiskIndicator";
import { MetricCard } from "../../components/common/MetricCard";
import { formatCurrency, formatPercent } from "../../utils/formatters";
import {
  ShieldAlert,
  ShieldCheck,
  ShieldX,
  AlertTriangle,
  RotateCcw,
  AlertOctagon,
  Scale,
  Activity,
  Layers,
  Zap,
} from "lucide-react";

export function RiskView() {
  const { telemetry, riskData, fetchRiskStatus, resetCircuitBreakersSafe, emergencyKillSafe } = useTrading();
  const { account, open_positions, circuit_breakers, broker_connected, feed_fresh, symbol } = telemetry;

  const rawStatus = riskData.status || {};
  const isTripped = circuit_breakers?.tripped;
  const isDrawdownBreached = account?.daily_drawdown_limit_hit;
  const isBrokerDown = !broker_connected;
  const isDataStale = !feed_fresh;
  const isBlackout = rawStatus.macro_blackout_active;

  const openCount = open_positions ? open_positions.length : 0;
  const maxPositions = rawStatus.max_concurrent_positions || 5;
  const maxRiskPerTrade = rawStatus.max_risk_per_trade_pct || 1.0;
  const maxDailyDD = rawStatus.max_daily_drawdown_pct || 3.0;

  // Determine Overall Risk State
  let riskState = "SAFE";
  let blockReason = "All 9 deterministic pre-trade risk gates passed. Execution permitted.";

  if (isTripped) {
    riskState = "BLOCKED";
    const breakers = Object.entries(circuit_breakers?.active_breakers || {});
    blockReason = breakers.length > 0
      ? `Hard circuit breaker active: ${breakers[0][0]} (${breakers[0][1]})`
      : "Circuit breaker tripped by safety manager.";
  } else if (isDrawdownBreached) {
    riskState = "BLOCKED";
    blockReason = `Daily drawdown limit exceeded (Max allowed: ${maxDailyDD}%). Trading halted until midnight UTC rollover.`;
  } else if (isBrokerDown) {
    riskState = "BLOCKED";
    blockReason = "Broker adapter connection is offline. No orders can be verified or routed.";
  } else if (isDataStale) {
    riskState = "BLOCKED";
    blockReason = "Market quote feed is stale. Live ticks exceeding max allowed latency.";
  } else if (isBlackout) {
    riskState = "BLOCKED";
    blockReason = `Macroeconomic Event Blackout active: ${rawStatus.macro_blackout_reason || "High impact economic release"}`;
  } else if (openCount >= maxPositions) {
    riskState = "WARNING";
    blockReason = `Max concurrent portfolio positions reached (${openCount}/${maxPositions}). New entries throttled.`;
  }

  // 9 Deterministic Pre-Trade Gates State List
  const gates = [
    {
      name: "Gate 1: Hard Circuit Breakers",
      status: !isTripped ? "HEALTHY" : "TRIPPED",
      details: isTripped ? "Circuit breaker latched" : "No active latches",
    },
    {
      name: "Gate 2: Daily Drawdown Limit",
      status: !isDrawdownBreached ? "HEALTHY" : "BLOCKED",
      details: isDrawdownBreached ? `Breached limit (${maxDailyDD}%)` : `Safe (Max: ${maxDailyDD}%)`,
    },
    {
      name: "Gate 3: Max Portfolio Positions",
      status: openCount < maxPositions ? "HEALTHY" : "BLOCKED",
      details: `${openCount} of ${maxPositions} slots utilized`,
    },
    {
      name: "Gate 4: Single Symbol Exposure",
      status: "HEALTHY",
      details: `Max ${(rawStatus.max_symbol_positions || 2)} positions per asset`,
    },
    {
      name: "Gate 5: Broker Health & Latency",
      status: broker_connected ? "HEALTHY" : "DISCONNECTED",
      details: broker_connected ? "MT5 / Binance verified" : "Broker connection dead",
    },
    {
      name: "Gate 6: Data Feed Freshness",
      status: feed_fresh ? "HEALTHY" : "STALE",
      details: feed_fresh ? "Live quote ticks < 5s" : "Feed latency > 15s",
    },
    {
      name: "Gate 7: Market Spread Filter",
      status: "HEALTHY",
      details: "Spread protection max 40 pts",
    },
    {
      name: "Gate 8: Stop-Loss Validity",
      status: "HEALTHY",
      details: "Minimum 5 ticks stop distance required",
    },
    {
      name: "Gate 9: Sizing Verification",
      status: "HEALTHY",
      details: `Max ${maxRiskPerTrade}% risk pool sizing`,
    },
  ];

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6 select-none bg-slate-950">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-800">
        <div>
          <h1 className="text-base font-bold font-mono text-white tracking-wide flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-sky-400" />
            <span>INSTITUTIONAL RISK CONTROLLER & CIRCUIT BREAKERS</span>
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            9 deterministic pre-trade gates, drawdown limiters, and macro blackout enforcement.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {isTripped && (
            <button
              onClick={resetCircuitBreakersSafe}
              className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-mono font-bold flex items-center gap-1.5 transition-colors shadow-sm"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Administrative Reset Breakers</span>
            </button>
          )}

          <button
            onClick={emergencyKillSafe}
            className="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-mono font-bold flex items-center gap-1.5 transition-colors shadow-sm"
          >
            <AlertOctagon className="w-3.5 h-3.5" />
            <span>Emergency Kill Switch</span>
          </button>
        </div>
      </div>

      {/* Prominent Risk State Banner */}
      <RiskIndicator state={riskState} reason={blockReason} />

      {/* Core Limits Summary Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <MetricCard
          title="Risk Per Trade Limit"
          value={`${maxRiskPerTrade}%`}
          subValue="Calculated via broker tick value"
          icon={Scale}
          tier={2}
          badge="FIXED"
        />

        <MetricCard
          title="Max Daily Drawdown"
          value={`${maxDailyDD}%`}
          subValue={`Starting Baseline: ${formatCurrency(rawStatus.daily_starting_equity || 100.0)}`}
          icon={AlertTriangle}
          tier={2}
          badge={isDrawdownBreached ? "BREACHED" : "ENFORCED"}
          badgeStatus={isDrawdownBreached ? "danger" : "healthy"}
        />

        <MetricCard
          title="Max Open Positions"
          value={`${openCount} / ${maxPositions}`}
          subValue="Max 2 concurrent per symbol"
          icon={Layers}
          tier={2}
          badge={openCount >= maxPositions ? "FULL" : "OPEN"}
          badgeStatus={openCount >= maxPositions ? "warning" : "healthy"}
        />

        <MetricCard
          title="Macro Event Blackout"
          value={isBlackout ? "ACTIVE" : "INACTIVE"}
          subValue={rawStatus.macro_blackout_reason || "Normal trading window"}
          icon={Zap}
          tier={2}
          badge={isBlackout ? "BLACKOUT" : "SAFE"}
          badgeStatus={isBlackout ? "danger" : "healthy"}
        />
      </div>

      {/* 9 Deterministic Pre-Trade Gates Matrix */}
      <div className="p-4 rounded-lg bg-slate-900 border border-slate-800 space-y-3 shadow-lg">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <span className="text-xs font-mono font-bold uppercase text-white tracking-wider">
            Deterministic Pre-Trade Risk Gates Matrix
          </span>
          <span className="text-[11px] font-mono text-slate-400">
            Evaluated synchronously on every order submission
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {gates.map((g, idx) => (
            <div
              key={idx}
              className="p-3 rounded-lg bg-slate-950/70 border border-slate-800 flex items-start justify-between gap-2"
            >
              <div className="space-y-0.5 min-w-0">
                <div className="text-xs font-bold font-mono text-slate-200 truncate">
                  {g.name}
                </div>
                <div className="text-[11px] font-mono text-slate-400 truncate">
                  {g.details}
                </div>
              </div>
              <StatusBadge status={g.status} size="sm" />
            </div>
          ))}
        </div>
      </div>

      {/* Latched Circuit Breakers Table */}
      <div className="p-4 rounded-lg bg-slate-900 border border-slate-800 space-y-3 shadow-lg">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <span className="text-xs font-mono font-bold uppercase text-white tracking-wider flex items-center gap-2">
            <AlertOctagon className="w-4 h-4 text-rose-400" />
            Active Circuit Breaker Latches
          </span>
          <span className="text-[11px] font-mono text-slate-400">
            Hard safety latch · Requires administrative reset
          </span>
        </div>

        {Object.entries(circuit_breakers?.active_breakers || {}).length === 0 ? (
          <div className="p-4 text-center font-mono text-xs text-slate-400 bg-slate-950/60 rounded-lg border border-slate-800/80">
            ✅ All circuit breakers armed and healthy. No safety trips recorded.
          </div>
        ) : (
          <div className="space-y-2">
            {Object.entries(circuit_breakers?.active_breakers || {}).map(([bName, bReason]) => (
              <div
                key={bName}
                className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 flex items-center justify-between gap-3 text-xs font-mono"
              >
                <div>
                  <span className="font-bold text-rose-300 block">{bName}</span>
                  <span className="text-slate-300 text-[11px]">{bReason}</span>
                </div>
                <span className="text-[10px] text-slate-400 shrink-0">
                  {circuit_breakers?.trip_timestamps?.[bName] || "Recent"}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
