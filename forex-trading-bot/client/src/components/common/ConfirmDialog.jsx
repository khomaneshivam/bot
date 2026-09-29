import React, { useState } from "react";
import { AlertTriangle, ShieldAlert, CheckCircle2, XCircle } from "lucide-react";

export function ConfirmDialog({
  isOpen,
  title,
  description,
  warningNote,
  confirmWord, // If present, requires typing this exact word (e.g. "LIVE" or "RESET")
  confirmLabel = "Confirm Action",
  confirmVariant = "danger", // "danger" | "warning" | "primary"
  checklist = [], // [{ label: "Broker Connected", ok: true }, ...]
  onConfirm,
  onCancel,
}) {
  const [typedInput, setTypedInput] = useState("");

  if (!isOpen) return null;

  const requiresInput = Boolean(confirmWord);
  const isInputValid = !requiresInput || typedInput.trim().toUpperCase() === confirmWord.toUpperCase();
  const allChecksPassed = checklist.every((item) => item.ok);

  const canConfirm = isInputValid && allChecksPassed;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 select-none animate-fadeIn">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        className="w-full max-w-md bg-slate-900 border border-slate-700 rounded-xl shadow-2xl overflow-hidden"
      >
        {/* Header */}
        <div className="px-5 py-4 border-b border-slate-800 flex items-center gap-3 bg-slate-950/60">
          <div
            className={`p-2 rounded-lg ${
              confirmVariant === "danger"
                ? "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                : "bg-amber-500/20 text-amber-400 border border-amber-500/30"
            }`}
          >
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <h2 id="confirm-dialog-title" className="text-sm font-bold text-white font-mono tracking-wide">
              {title}
            </h2>
            <div className="text-[11px] text-slate-400 font-mono">Privileged Control Gate</div>
          </div>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4 text-xs">
          <p className="text-slate-300 leading-relaxed">{description}</p>

          {warningNote && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
              <div className="text-[11px] leading-relaxed">{warningNote}</div>
            </div>
          )}

          {/* Pre-flight checklist if provided */}
          {checklist.length > 0 && (
            <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 space-y-1.5 font-mono text-[11px]">
              <div className="text-slate-400 uppercase text-[10px] tracking-wider mb-1">
                Pre-Flight Safety Verification:
              </div>
              {checklist.map((item, idx) => (
                <div key={idx} className="flex items-center justify-between">
                  <span className="text-slate-300">{item.label}</span>
                  <span className="flex items-center gap-1 font-bold">
                    {item.ok ? (
                      <>
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        <span className="text-emerald-400">PASSED</span>
                      </>
                    ) : (
                      <>
                        <XCircle className="w-3.5 h-3.5 text-rose-400" />
                        <span className="text-rose-400">BLOCKED</span>
                      </>
                    )}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Typed confirmation input if required */}
          {requiresInput && (
            <div className="space-y-1.5">
              <label className="block text-[11px] font-mono text-slate-400">
                To confirm, type <strong className="text-white bg-slate-800 px-1.5 py-0.5 rounded">{confirmWord}</strong> below:
              </label>
              <input
                type="text"
                value={typedInput}
                onChange={(e) => setTypedInput(e.target.value)}
                placeholder={`Type "${confirmWord}" to verify`}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-white font-mono text-xs focus:outline-none focus:border-rose-500 uppercase"
                autoFocus
              />
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3.5 bg-slate-950/80 border-t border-slate-800 flex items-center justify-end gap-2.5">
          <button
            onClick={() => {
              setTypedInput("");
              onCancel();
            }}
            className="px-4 py-2 rounded-lg text-xs font-mono font-medium text-slate-400 hover:text-white bg-slate-800/80 hover:bg-slate-800 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              if (canConfirm) {
                setTypedInput("");
                onConfirm();
              }
            }}
            disabled={!canConfirm}
            className={`px-4 py-2 rounded-lg text-xs font-mono font-bold transition-all shadow-md ${
              !canConfirm
                ? "bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700/50"
                : confirmVariant === "danger"
                ? "bg-rose-600 hover:bg-rose-500 text-white shadow-rose-900/30"
                : "bg-amber-600 hover:bg-amber-500 text-white shadow-amber-900/30"
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
