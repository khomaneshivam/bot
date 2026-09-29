import React, { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import {
  Lock,
  User,
  Key,
  KeyRound,
  X,
  AlertCircle,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";

export function LoginModal() {
  const { isLoginModalOpen, setIsLoginModalOpen, login, register, authError, setAuthError } = useAuth();

  const [mode, setMode] = useState("login"); // "login" | "register"
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [role, setRole] = useState("TRADER");
  const [adminKey, setAdminKey] = useState("");
  const [riskAcknowledged, setRiskAcknowledged] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isLoginModalOpen) return null;

  const hasMinLength = password.length >= 8;
  const hasLetter = /[a-zA-Z]/.test(password);
  const hasNumber = /[0-9]/.test(password);
  const passwordsMatch = password.length > 0 && password === confirmPassword;
  const isUsernameValid = /^[a-zA-Z0-9_-]{3,32}$/.test(username.trim());

  const canRegister =
    isUsernameValid &&
    hasMinLength &&
    hasLetter &&
    hasNumber &&
    passwordsMatch &&
    riskAcknowledged &&
    (role !== "ADMIN" || adminKey.trim().length > 0);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    if (mode === "login") {
      await login(username.trim(), password);
    } else {
      if (!canRegister) {
        setIsSubmitting(false);
        return;
      }
      await register({
        username: username.trim(),
        password,
        confirmPassword,
        role,
        adminKey: role === "ADMIN" ? adminKey.trim() : null,
      });
    }
    setIsSubmitting(false);
  };

  const handleQuickFill = (u, p) => {
    setUsername(u);
    setPassword(p);
    setMode("login");
    setAuthError(null);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 select-none animate-fadeIn">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="login-dialog-title"
        className="w-full max-w-md bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl overflow-hidden"
      >
        {/* Header */}
        <div className="px-5 py-3.5 border-b border-slate-800 flex items-center justify-between bg-slate-950/80">
          <div className="flex items-center gap-2">
            {mode === "login" ? (
              <Lock className="w-4 h-4 text-sky-400" />
            ) : (
              <Sparkles className="w-4 h-4 text-sky-400" />
            )}
            <h2 id="login-dialog-title" className="text-sm font-bold text-white font-mono">
              {mode === "login" ? "Terminal Authentication" : "Register Operator Profile"}
            </h2>
          </div>
          <button
            onClick={() => setIsLoginModalOpen(false)}
            className="p-1 rounded text-slate-400 hover:text-white"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tab Switcher */}
        <div className="px-5 pt-4">
          <div className="grid grid-cols-2 p-1 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono">
            <button
              type="button"
              onClick={() => {
                setMode("login");
                setAuthError(null);
              }}
              className={`py-1.5 rounded-lg font-semibold transition-all ${
                mode === "login"
                  ? "bg-slate-800 text-white shadow-sm border border-slate-700"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                setMode("register");
                setAuthError(null);
              }}
              className={`py-1.5 rounded-lg font-semibold transition-all ${
                mode === "register"
                  ? "bg-slate-800 text-white shadow-sm border border-slate-700"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Register
            </button>
          </div>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-5 space-y-3.5 text-xs font-mono">
          {authError && (
            <div className="p-2.5 rounded bg-rose-500/10 border border-rose-500/30 text-rose-300 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>{authError}</span>
            </div>
          )}

          {/* Username */}
          <div className="space-y-1">
            <label className="text-slate-300 block text-[11px]">
              OPERATOR USERNAME {mode === "register" && <span className="text-slate-500">(3-32 chars)</span>}
            </label>
            <div className="relative">
              <User className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-white font-mono focus:outline-none focus:border-sky-500"
                placeholder="Username"
              />
            </div>
          </div>

          {/* Password */}
          <div className="space-y-1">
            <label className="text-slate-300 block text-[11px]">
              PASSPHRASE {mode === "register" && <span className="text-slate-500">(Min 8 chars, 1 num)</span>}
            </label>
            <div className="relative">
              <Key className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-white font-mono focus:outline-none focus:border-sky-500"
                placeholder="Passphrase"
              />
            </div>
          </div>

          {/* Register Mode Extra Fields */}
          {mode === "register" && (
            <div className="space-y-3 pt-1">
              <div className="space-y-1">
                <label className="text-slate-300 block text-[11px]">CONFIRM PASSPHRASE</label>
                <div className="relative">
                  <KeyRound className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-white font-mono focus:outline-none focus:border-sky-500"
                    placeholder="Repeat passphrase"
                  />
                </div>
              </div>

              {/* Password Quality Indicator */}
              <div className="p-2 rounded bg-slate-950 border border-slate-800 text-[10px] grid grid-cols-2 gap-1 text-slate-400">
                <div className={`flex items-center gap-1 ${hasMinLength ? "text-emerald-400" : "text-slate-500"}`}>
                  <CheckCircle2 className="w-3 h-3" />
                  <span>8+ Chars</span>
                </div>
                <div className={`flex items-center gap-1 ${hasNumber ? "text-emerald-400" : "text-slate-500"}`}>
                  <CheckCircle2 className="w-3 h-3" />
                  <span>Number</span>
                </div>
                <div className={`flex items-center gap-1 ${hasLetter ? "text-emerald-400" : "text-slate-500"}`}>
                  <CheckCircle2 className="w-3 h-3" />
                  <span>Letter</span>
                </div>
                <div className={`flex items-center gap-1 ${passwordsMatch ? "text-emerald-400" : "text-slate-500"}`}>
                  <CheckCircle2 className="w-3 h-3" />
                  <span>Match</span>
                </div>
              </div>

              {/* Role Selection */}
              <div className="space-y-1">
                <label className="text-slate-300 block text-[11px]">ROLE</label>
                <div className="grid grid-cols-3 gap-1.5">
                  <button
                    type="button"
                    onClick={() => setRole("TRADER")}
                    className={`py-1.5 rounded border text-center ${
                      role === "TRADER"
                        ? "bg-sky-500/20 text-sky-300 border-sky-500 font-bold"
                        : "bg-slate-950 text-slate-400 border-slate-800"
                    }`}
                  >
                    TRADER
                  </button>
                  <button
                    type="button"
                    onClick={() => setRole("READ_ONLY")}
                    className={`py-1.5 rounded border text-center ${
                      role === "READ_ONLY"
                        ? "bg-slate-800 text-white border-slate-600 font-bold"
                        : "bg-slate-950 text-slate-400 border-slate-800"
                    }`}
                  >
                    VIEWER
                  </button>
                  <button
                    type="button"
                    onClick={() => setRole("ADMIN")}
                    className={`py-1.5 rounded border text-center ${
                      role === "ADMIN"
                        ? "bg-purple-500/20 text-purple-300 border-purple-500 font-bold"
                        : "bg-slate-950 text-slate-400 border-slate-800"
                    }`}
                  >
                    ADMIN
                  </button>
                </div>
              </div>

              {role === "ADMIN" && (
                <div className="space-y-1">
                  <label className="text-purple-300 block text-[11px]">ADMIN KEY</label>
                  <input
                    type="password"
                    value={adminKey}
                    onChange={(e) => setAdminKey(e.target.value)}
                    required
                    placeholder="Enter Admin Master Key"
                    className="w-full px-3 py-2 bg-slate-950 border border-purple-500/50 rounded-lg text-purple-200"
                  />
                </div>
              )}

              {/* Risk checkbox */}
              <label className="flex items-start gap-2 pt-1 text-[10px] text-amber-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={riskAcknowledged}
                  onChange={(e) => setRiskAcknowledged(e.target.checked)}
                  className="mt-0.5 rounded border-amber-500 text-amber-500 focus:ring-0"
                />
                <span>I acknowledge autonomous execution risks and regulatory rules.</span>
              </label>
            </div>
          )}

          {/* Quick Demo Credentials in Sign In Mode */}
          {mode === "login" && (
            <div className="pt-1 border-t border-slate-800 space-y-1.5">
              <span className="text-[10px] text-slate-500 block uppercase">Quick Fill:</span>
              <div className="grid grid-cols-3 gap-1 text-[10px]">
                <button
                  type="button"
                  onClick={() => handleQuickFill("admin", "AdminTrading2026!")}
                  className="py-1 px-1 rounded bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-300"
                >
                  Admin
                </button>
                <button
                  type="button"
                  onClick={() => handleQuickFill("trader", "TraderTrading2026!")}
                  className="py-1 px-1 rounded bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-300"
                >
                  Trader
                </button>
                <button
                  type="button"
                  onClick={() => handleQuickFill("viewer", "ViewerTrading2026!")}
                  className="py-1 px-1 rounded bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-300"
                >
                  Viewer
                </button>
              </div>
            </div>
          )}

          {/* Modal Actions */}
          <div className="pt-2 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setIsLoginModalOpen(false)}
              className="px-3 py-2 rounded-lg text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || (mode === "register" && !canRegister)}
              className="px-4 py-2 rounded-lg font-bold bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white shadow-md shadow-sky-600/30"
            >
              {isSubmitting
                ? "Processing..."
                : mode === "login"
                ? "Sign In"
                : "Create Account"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
