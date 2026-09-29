import React from "react";

/**
 * Institutional StatusBadge
 * CRITICAL RULE: Never use color alone. Always provides icon + label + semantic tone.
 */
export function StatusBadge({ status, label, icon: CustomIcon, size = "md", className = "" }) {
  const norm = (status || "UNKNOWN").toUpperCase();

  let colorClasses = "bg-slate-800 text-slate-300 border-slate-700";
  let dotColor = "bg-slate-400";
  let displayLabel = label || norm;

  if (norm.includes("HEALTHY") || norm === "ONLINE" || norm === "SAFE" || norm === "FILLED" || norm === "MATCH" || norm === "SYNCHRONIZED" || norm === "APPROVED") {
    colorClasses = "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
    dotColor = "bg-emerald-400";
  } else if (norm.includes("WARN") || norm === "PENDING" || norm === "SUBMITTED" || norm === "PARTIAL" || norm === "DEGRADED") {
    colorClasses = "bg-amber-500/10 text-amber-400 border-amber-500/30";
    dotColor = "bg-amber-400";
  } else if (norm.includes("DANGER") || norm === "BLOCKED" || norm === "REJECTED" || norm === "DISCONNECTED" || norm === "CRITICAL" || norm === "MISMATCH" || norm === "HALTED" || norm === "TRIPPED") {
    colorClasses = "bg-rose-500/10 text-rose-400 border-rose-500/30";
    dotColor = "bg-rose-500 animate-pulse";
  } else if (norm === "INFO" || norm === "ARMED" || norm === "CREATED") {
    colorClasses = "bg-sky-500/10 text-sky-400 border-sky-500/30";
    dotColor = "bg-sky-400";
  }

  const sizeClasses = size === "sm" 
    ? "px-2 py-0.5 text-[10px]" 
    : size === "lg" 
    ? "px-3 py-1 text-xs" 
    : "px-2.5 py-0.5 text-[11px]";

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-mono font-semibold rounded-md border tracking-wider uppercase select-none ${sizeClasses} ${colorClasses} ${className}`}
    >
      {CustomIcon ? (
        <CustomIcon className="w-3 h-3" />
      ) : (
        <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dotColor}`} />
      )}
      <span>{displayLabel}</span>
    </span>
  );
}
