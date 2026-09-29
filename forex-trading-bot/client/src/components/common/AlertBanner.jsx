import React from "react";
import { AlertTriangle, AlertOctagon, Info, X } from "lucide-react";

export function AlertBanner({
  severity = "CRITICAL",
  title,
  message,
  actionLabel,
  onAction,
  onDismiss,
  className = "",
}) {
  const norm = String(severity).toUpperCase();

  let config = {
    bg: "bg-rose-950/80 border-rose-600 text-rose-200",
    badgeBg: "bg-rose-600 text-white",
    icon: AlertOctagon,
    titleColor: "text-rose-100",
  };

  if (norm === "WARNING") {
    config = {
      bg: "bg-amber-950/80 border-amber-600 text-amber-200",
      badgeBg: "bg-amber-600 text-white",
      icon: AlertTriangle,
      titleColor: "text-amber-100",
    };
  } else if (norm === "INFO") {
    config = {
      bg: "bg-sky-950/80 border-sky-600 text-sky-200",
      badgeBg: "bg-sky-600 text-white",
      icon: Info,
      titleColor: "text-sky-100",
    };
  }

  const IconComponent = config.icon;

  return (
    <div
      role="alert"
      className={`px-4 py-2.5 border-b shadow-xl flex items-center justify-between gap-4 z-40 select-none ${config.bg} ${className}`}
    >
      <div className="flex items-center gap-3 min-w-0">
        <div className="p-1 rounded bg-black/30 shrink-0">
          <IconComponent className="w-5 h-5 text-current animate-pulse" />
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className={`text-[10px] font-mono font-black uppercase px-1.5 py-0.5 rounded ${config.badgeBg}`}>
              {norm}
            </span>
            <span className={`text-xs font-bold font-mono tracking-wide ${config.titleColor}`}>
              {title}
            </span>
          </div>
          <div className="text-xs text-slate-300 mt-0.5 truncate">
            {message}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        {actionLabel && onAction && (
          <button
            onClick={onAction}
            className="px-3 py-1 text-xs font-mono font-bold rounded bg-slate-900/90 hover:bg-black text-white border border-slate-700 transition-colors"
          >
            {actionLabel}
          </button>
        )}
        {onDismiss && (
          <button
            onClick={onDismiss}
            aria-label="Dismiss alert"
            className="p-1 rounded hover:bg-black/20 text-slate-400 hover:text-white"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}
