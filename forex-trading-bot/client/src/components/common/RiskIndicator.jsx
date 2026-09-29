import React from "react";
import { ShieldCheck, ShieldAlert, ShieldX } from "lucide-react";

export function RiskIndicator({ state = "SAFE", reason = "", details = "" }) {
  const normState = String(state).toUpperCase();

  let config = {
    label: "RISK: SAFE",
    bg: "bg-emerald-500/10 border-emerald-500/30",
    text: "text-emerald-400",
    icon: ShieldCheck,
    desc: "All deterministic risk gates passed. Autonomous execution permitted.",
  };

  if (normState === "WARNING" || normState.includes("WARN")) {
    config = {
      label: "RISK: ELEVATED WARNING",
      bg: "bg-amber-500/10 border-amber-500/30",
      text: "text-amber-400",
      icon: ShieldAlert,
      desc: reason || "Market spread or volatility approaching risk thresholds.",
    };
  } else if (normState === "BLOCKED" || normState.includes("TRIP") || normState.includes("HALT") || normState.includes("BREACH")) {
    config = {
      label: "RISK: NEW TRADES BLOCKED",
      bg: "bg-rose-500/15 border-rose-500/40",
      text: "text-rose-400",
      icon: ShieldX,
      desc: reason || "Deterministic safety gate tripped. Check circuit breakers.",
    };
  }

  const IconComponent = config.icon;

  return (
    <div className={`p-3 rounded-lg border ${config.bg} flex items-start gap-3 select-none`}>
      <div className={`p-1.5 rounded-md bg-slate-950/60 ${config.text} shrink-0`}>
        <IconComponent className="w-5 h-5" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <span className={`text-xs font-mono font-bold tracking-wide uppercase ${config.text}`}>
            {config.label}
          </span>
          <span className="text-[10px] font-mono text-slate-400">Deterministic Gate</span>
        </div>
        <div className="text-xs font-medium text-slate-200 mt-0.5">
          {config.desc}
        </div>
        {details && (
          <div className="text-[11px] font-mono text-slate-400 mt-1 pt-1 border-t border-slate-800">
            {details}
          </div>
        )}
      </div>
    </div>
  );
}
