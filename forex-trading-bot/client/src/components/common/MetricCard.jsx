import React from "react";

export function MetricCard({
  title,
  value,
  subValue,
  change,
  changeType, // "positive" | "negative" | "neutral"
  tier = 2,
  badge,
  badgeStatus,
  icon: Icon,
  className = "",
}) {
  const tierClasses = tier === 1
    ? "p-4 bg-slate-900/90 border border-slate-700/80 shadow-lg"
    : tier === 2
    ? "p-3.5 bg-slate-900/60 border border-slate-800"
    : "p-3 bg-slate-950/70 border border-slate-800/60";

  const valueSize = tier === 1
    ? "text-xl sm:text-2xl font-black"
    : tier === 2
    ? "text-lg sm:text-xl font-bold"
    : "text-base font-semibold";

  return (
    <div className={`rounded-lg flex flex-col justify-between transition-all ${tierClasses} ${className}`}>
      {/* Card Header */}
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-1.5">
          {Icon && <Icon className="w-3.5 h-3.5 text-slate-400" />}
          <span className="text-[11px] font-mono font-medium text-slate-400 uppercase tracking-wider">
            {title}
          </span>
        </div>
        {badge && (
          <span
            className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded border ${
              badgeStatus === "danger"
                ? "bg-rose-500/10 text-rose-400 border-rose-500/30"
                : badgeStatus === "warning"
                ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                : badgeStatus === "healthy"
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                : "bg-slate-800 text-slate-300 border-slate-700"
            }`}
          >
            {badge}
          </span>
        )}
      </div>

      {/* Main Metric Value */}
      <div className="flex items-baseline justify-between gap-2 my-1">
        <div className={`font-mono tabular-nums text-slate-100 ${valueSize}`}>
          {value !== undefined && value !== null ? value : "--"}
        </div>
        {change && (
          <span
            className={`text-xs font-mono font-bold px-1.5 py-0.5 rounded ${
              changeType === "positive"
                ? "text-emerald-400 bg-emerald-500/10"
                : changeType === "negative"
                ? "text-rose-400 bg-rose-500/10"
                : "text-slate-400 bg-slate-800"
            }`}
          >
            {change}
          </span>
        )}
      </div>

      {/* Subtext / Details */}
      {subValue && (
        <div className="text-[11px] font-mono text-slate-400 mt-1 pt-1 border-t border-slate-800/60 truncate">
          {subValue}
        </div>
      )}
    </div>
  );
}
