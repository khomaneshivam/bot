import React from "react";
import { useTrading } from "../../context/TradingContext";
import { MetricCard } from "../../components/common/MetricCard";
import { RiskIndicator } from "../../components/common/RiskIndicator";
import { StatusBadge } from "../../components/common/StatusBadge";
import { formatCurrency, formatPnL, formatPercent, getPnLTextColor } from "../../utils/formatters";
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  Shield,
  Layers,
  Scale,
  Activity,
  Cpu,
  Server,
  AlertTriangle,
  ArrowRight,
} from "lucide-react";

export function DashboardView() {
  const { telemetry, reconciliationData, setActiveView, emergencyKillSafe } = useTrading();
  const { account, open_positions, strategies, ml_stats, circuit_breakers, broker_connected, feed_fresh } = telemetry;

  const totalTrades = account?.total_trades || 0;
  const realizedPnL = account?.realized_pnl || 0.0;
  const unrealizedPnL = account?.unrealized_pnl || 0.0;
  const equity = account?.equity || 100.0;
  const balance = account?.balance || 100.0;
  const openCount = open_positions ? open_positions.length : 0;
  const winRate = account?.win_rate || 0.0;

  // Calculate total portfolio exposure in units / currency
  const totalExposure = (open_positions || []).reduce(
    (sum, pos) => sum + (Number(pos.size) * Number(pos.current_price || pos.entry_price || 0)),
    0
  );

  const isDesynced = reconciliationData.has_active_mismatch;
  const isTripped = circuit_breakers?.tripped;
  const isDrawdownBreached = account?.daily_drawdown_limit_hit;

  const riskState = isTripped || isDrawdownBreached || isDesynced ? "BLOCKED" : "SAFE";
  const riskReason = isDesynced
    ? "Broker reconciliation mismatch detected. New trades blocked."
    : isTripped
    ? Object.values(circuit_breakers?.active_breakers || {})[0] || "Circuit breaker active."
    : isDrawdownBreached
    ? "Daily drawdown limit exceeded. Autonomous entries locked."
    : "All risk parameters operating within normal parameters.";

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6 select-none bg-slate-950">
      {/* Top Welcome / Executive Summary Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
        <div>
          <h1 className="text-lg font-bold font-mono text-white tracking-wide flex items-center gap-2">
            <span>OPERATIONAL EXECUTIVE DASHBOARD</span>
            <StatusBadge status={riskState} label={riskState} size="sm" />
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            Institutional portfolio telemetry, multi-tier risk metrics, and fail-closed execution health.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveView("risk")}
            className="px-3 py-1.5 rounded-lg text-xs font-mono font-medium text-slate-300 hover:text-white bg-slate-900 hover:bg-slate-800 border border-slate-800 flex items-center gap-1.5 transition-colors"
          >
            <Shield className="w-3.5 h-3.5 text-sky-400" />
            <span>Risk Console</span>
          </button>
          <button
            onClick={() => setActiveView("positions")}
            className="px-3 py-1.5 rounded-lg text-xs font-mono font-medium text-slate-300 hover:text-white bg-slate-900 hover:bg-slate-800 border border-slate-800 flex items-center gap-1.5 transition-colors"
          >
            <Layers className="w-3.5 h-3.5 text-sky-400" />
            <span>Active Positions ({openCount})</span>
          </button>
        </div>
      </div>

      {/* Prominent Risk Banner */}
      <RiskIndicator
        state={riskState}
        reason={riskReason}
        details={
          isDesynced
            ? "CRITICAL: Reconciliation engine detected ghost/orphan position mismatch. Check Reconciliation page immediately."
            : null
        }
      />

      {/* TIER 1: CORE PORTFOLIO & RISK METRICS (Highest visual priority) */}
      <section aria-label="Tier 1 Financial Metrics" className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-mono font-bold uppercase tracking-widest text-slate-400">
            Tier 1: Capital & Exposure Overview
          </span>
          <span className="text-[10px] font-mono text-slate-500">Authoritative Broker Truth</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
          {/* Equity */}
          <MetricCard
            tier={1}
            title="Total Equity"
            value={formatCurrency(equity)}
            subValue={`Available Balance: ${formatCurrency(balance)}`}
            icon={Wallet}
            badge={(account?.mode || "PAPER").toUpperCase()}
            badgeStatus={account?.mode === "live" ? "danger" : "healthy"}
          />

          {/* Realized & Unrealized PnL */}
          <MetricCard
            tier={1}
            title="Realized / Floating P&L"
            value={formatPnL(realizedPnL)}
            subValue={`Floating: ${formatPnL(unrealizedPnL)}`}
            change={formatPnL(unrealizedPnL)}
            changeType={unrealizedPnL > 0 ? "positive" : unrealizedPnL < 0 ? "negative" : "neutral"}
            icon={realizedPnL >= 0 ? TrendingUp : TrendingDown}
          />

          {/* Daily Drawdown */}
          <MetricCard
            tier={1}
            title="Daily Drawdown"
            value={isDrawdownBreached ? "BREACHED" : "NORMAL"}
            subValue="Limit: 3.0% Max Daily Loss"
            icon={Shield}
            badge={isDrawdownBreached ? "LOCKED" : "SAFE"}
            badgeStatus={isDrawdownBreached ? "danger" : "healthy"}
          />

          {/* Open Exposure */}
          <MetricCard
            tier={1}
            title="Total Open Exposure"
            value={totalExposure > 0 ? formatCurrency(totalExposure) : "$0.00"}
            subValue={`${openCount} open position${openCount === 1 ? "" : "s"}`}
            icon={Scale}
            badge={`${openCount}/5 MAX`}
            badgeStatus={openCount >= 4 ? "warning" : "neutral"}
          />
        </div>
      </section>

      {/* TIER 2: SYSTEM, BROKER, MODEL & EXECUTION STATE */}
      <section aria-label="Tier 2 Infrastructure & Engine State" className="space-y-2">
        <span className="text-[11px] font-mono font-bold uppercase tracking-widest text-slate-400">
          Tier 2: System Telemetry & Model Status
        </span>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {/* Broker Status */}
          <div className="p-3.5 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center justify-between">
            <div>
              <div className="text-[10px] font-mono uppercase text-slate-400">Broker Adapter</div>
              <div className="text-sm font-bold font-mono text-white mt-0.5">
                {broker_connected ? "MT5 / BINANCE LIVE" : "DISCONNECTED"}
              </div>
              <div className="text-[10px] font-mono text-slate-400 mt-1">
                Feed: {feed_fresh ? "Real-time Fresh" : "Stale / Delayed"}
              </div>
            </div>
            <StatusBadge status={broker_connected ? "ONLINE" : "DISCONNECTED"} />
          </div>

          {/* Model Observability */}
          <div className="p-3.5 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center justify-between">
            <div>
              <div className="text-[10px] font-mono uppercase text-slate-400">ML Model Engine</div>
              <div className="text-sm font-bold font-mono text-white mt-0.5">
                v{ml_stats?.version || "1.0.0"} (Champion)
              </div>
              <div className="text-[10px] font-mono text-slate-400 mt-1">
                Vetoes: {ml_stats?.vetoed_trades_count || 0} setups
              </div>
            </div>
            <StatusBadge status={ml_stats?.is_trained ? "ONLINE" : "INITIALIZING"} />
          </div>

          {/* Win Rate & Profit Factor */}
          <div className="p-3.5 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center justify-between">
            <div>
              <div className="text-[10px] font-mono uppercase text-slate-400">Execution Win Rate</div>
              <div className="text-sm font-bold font-mono text-white mt-0.5">
                {winRate}% <span className="text-xs text-slate-400 font-normal">({totalTrades} trades)</span>
              </div>
              <div className="text-[10px] font-mono text-slate-400 mt-1">
                Wins: {account?.winning_trades || 0} | Losses: {account?.losing_trades || 0}
              </div>
            </div>
            <StatusBadge status="INFO" label={`PF ${account?.profit_factor || "1.0"}`} />
          </div>

          {/* Reconciliation Status */}
          <div className="p-3.5 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center justify-between">
            <div>
              <div className="text-[10px] font-mono uppercase text-slate-400">Reconciliation</div>
              <div className="text-sm font-bold font-mono text-white mt-0.5">
                {isDesynced ? "MISMATCH DETECTED" : "SYNCHRONIZED"}
              </div>
              <div className="text-[10px] font-mono text-slate-400 mt-1">
                {isDesynced ? "Ghost position found" : "0 Discrepancies"}
              </div>
            </div>
            <StatusBadge status={isDesynced ? "MISMATCH" : "SYNCHRONIZED"} />
          </div>
        </div>
      </section>

      {/* TIER 3: RECENT AUDIT ACTIVITY & STRATEGY ATTRIBUTION */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Strategy Ensemble Overview */}
        <div className="p-4 rounded-lg bg-slate-900/50 border border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-bold text-white uppercase flex items-center gap-2">
              <Activity className="w-4 h-4 text-sky-400" />
              Strategy Ensemble Allocation
            </span>
            <button
              onClick={() => setActiveView("strategies")}
              className="text-[11px] font-mono text-sky-400 hover:text-sky-300 flex items-center gap-1"
            >
              <span>View Strategies</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div className="space-y-2">
            {Object.entries(strategies || {}).length === 0 ? (
              <div className="text-xs text-slate-400 font-mono py-4 text-center">
                Initializing strategy weights...
              </div>
            ) : (
              Object.entries(strategies || {}).map(([name, data]) => {
                const chance = data.chance_pct || 0;
                const sig = data.signal || "HOLD";
                return (
                  <div key={name} className="p-2 rounded bg-slate-950/60 border border-slate-800/80">
                    <div className="flex justify-between items-center text-xs font-mono mb-1">
                      <span className="text-slate-200 font-semibold">{name.replace(/_/g, " ")}</span>
                      <span className={sig === "BUY" ? "text-emerald-400 font-bold" : sig === "SELL" ? "text-rose-400 font-bold" : "text-slate-400"}>
                        {sig} ({chance}%)
                      </span>
                    </div>
                    <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${sig === "BUY" ? "bg-emerald-500" : sig === "SELL" ? "bg-rose-500" : "bg-slate-600"}`}
                        style={{ width: `${Math.min(chance, 100)}%` }}
                      />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Live Risk & Engine Telemetry Logs */}
        <div className="p-4 rounded-lg bg-slate-900/50 border border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-bold text-white uppercase flex items-center gap-2">
              <Server className="w-4 h-4 text-sky-400" />
              Live Operational Telemetry
            </span>
            <button
              onClick={() => setActiveView("audit")}
              className="text-[11px] font-mono text-sky-400 hover:text-sky-300 flex items-center gap-1"
            >
              <span>Full Audit Log</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div className="space-y-1.5 max-h-56 overflow-y-auto pr-1 font-mono text-[11px]">
            {(telemetry.logs || []).slice(0, 8).map((log, idx) => (
              <div
                key={idx}
                className="p-2 rounded bg-slate-950/70 border border-slate-800/60 flex items-start gap-2"
              >
                <span className="text-slate-500 text-[10px] shrink-0">{log.time || "LOG"}</span>
                <span className="text-sky-400 font-semibold shrink-0">[{log.tag || "ENGINE"}]</span>
                <span className="text-slate-300 truncate">{log.message || log}</span>
              </div>
            ))}
            {(telemetry.logs || []).length === 0 && (
              <div className="text-xs text-slate-400 py-6 text-center">
                Waiting for engine logs...
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
