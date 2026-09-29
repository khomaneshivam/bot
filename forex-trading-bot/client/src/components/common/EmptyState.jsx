import React from "react";
import { Inbox } from "lucide-react";

export function EmptyState({
  title = "No Data Available",
  description = "There are no records matching your current filter.",
  icon: Icon = Inbox,
  actionLabel,
  onAction,
  className = "",
}) {
  return (
    <div className={`p-8 rounded-lg border border-slate-800 bg-slate-950/40 text-center flex flex-col items-center justify-center select-none ${className}`}>
      <div className="w-12 h-12 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500 mb-3 shadow-inner">
        <Icon className="w-6 h-6" />
      </div>
      <h3 className="text-xs font-mono font-bold text-slate-200 uppercase tracking-wider mb-1">
        {title}
      </h3>
      <p className="text-xs text-slate-400 max-w-sm mb-4 leading-relaxed">
        {description}
      </p>
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="px-3.5 py-1.5 rounded-lg text-xs font-mono font-bold bg-slate-800 hover:bg-slate-700 text-white border border-slate-700 transition-colors"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}
