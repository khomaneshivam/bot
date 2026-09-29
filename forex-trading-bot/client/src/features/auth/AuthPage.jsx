import React, { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import {
  Shield,
  Lock,
  User,
  KeyRound,
  Eye,
  EyeOff,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
  Server,
  Zap,
  HelpCircle,
  Sparkles,
} from "lucide-react";

export function AuthPage() {
  const { login, register, enterAsGuest, authError, setAuthError } = useAuth();

  const [mode, setMode] = useState("login"); // "login" | "register"
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [role, setRole] = useState("TRADER"); // "TRADER" | "READ_ONLY" | "ADMIN"
  const [adminKey, setAdminKey] = useState("");
  const [riskAcknowledged, setRiskAcknowledged] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Live password validation criteria
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
    setAuthError(null);
    setIsSubmitting(true);

    try {
      if (mode === "login") {
        if (!username || !password) {
          setAuthError("Please enter both username and password.");
          setIsSubmitting(false);
          return;
        }
        await login(username.trim(), password);
      } else {
        if (!canRegister) {
          setAuthError("Please complete all registration requirements.");
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
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleQuickFill = (u, p) => {
    setUsername(u);
    setPassword(p);
    setMode("login");
    setAuthError(null);
  };

  return (
    <div className="min-h-screen w-screen bg-slate-950 flex flex-col justify-between items-center p-4 sm:p-6 text-slate-100 select-none relative overflow-x-hidden">
      {/* Background Subtle Gradient Grid */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(14,165,233,0.15),rgba(255,255,255,0))] pointer-events-none" />

      {/* Top Brand Bar */}
      <header className="w-full max-w-5xl flex items-center justify-between py-4 border-b border-slate-900 z-10">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center font-black text-white text-base tracking-wider shadow-lg shadow-sky-500/20">
            Q
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold tracking-wider text-base text-white">
                QUANT<span className="text-sky-400">AI</span>
              </span>
              <span className="text-[10px] font-mono text-slate-400 px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800">
                PRO TERMINAL
              </span>
            </div>
            <p className="text-[11px] font-mono text-slate-500">Autonomous Financial Risk & Execution Gateway</p>
          </div>
        </div>

        {/* Security Invariant Badges */}
        <div className="hidden md:flex items-center gap-2 text-[10px] font-mono text-slate-400">
          <span className="flex items-center gap-1 px-2 py-1 rounded bg-slate-900/80 border border-slate-800">
            <ShieldCheck className="w-3 h-3 text-emerald-400" />
            Argon2id Hash
          </span>
          <span className="flex items-center gap-1 px-2 py-1 rounded bg-slate-900/80 border border-slate-800">
            <Lock className="w-3 h-3 text-sky-400" />
            HMAC-SHA256 Sessions
          </span>
          <span className="flex items-center gap-1 px-2 py-1 rounded bg-slate-900/80 border border-slate-800">
            <Server className="w-3 h-3 text-amber-400" />
            Strict RBAC
          </span>
        </div>
      </header>

      {/* Main Authentication Card */}
      <div className="w-full max-w-md my-auto py-8 z-10">
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl shadow-2xl p-6 sm:p-8 backdrop-blur-xl space-y-6">
          {/* Header & Mode Switcher */}
          <div className="text-center space-y-2">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-sky-500/10 border border-sky-500/20 text-sky-400 mb-1">
              {mode === "login" ? <Lock className="w-6 h-6" /> : <Sparkles className="w-6 h-6" />}
            </div>
            <h1 className="text-xl font-bold tracking-tight text-white">
              {mode === "login" ? "Operator Authentication" : "Register Operator Account"}
            </h1>
            <p className="text-xs text-slate-400 font-mono">
              {mode === "login"
                ? "Enter institutional credentials to access execution controls"
                : "Create an authorized cryptographic trading profile"}
            </p>
          </div>

          {/* Segmented Control Tabs */}
          <div className="grid grid-cols-2 p-1 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono">
            <button
              type="button"
              onClick={() => {
                setMode("login");
                setAuthError(null);
              }}
              className={`py-2 rounded-lg font-semibold transition-all ${
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
              className={`py-2 rounded-lg font-semibold transition-all ${
                mode === "register"
                  ? "bg-slate-800 text-white shadow-sm border border-slate-700"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Register
            </button>
          </div>

          {/* Error Alert Banner */}
          {authError && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-start gap-2 animate-fadeIn">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
              <div className="flex-1 font-mono">{authError}</div>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Username Input */}
            <div className="space-y-1.5">
              <label className="text-[11px] font-mono text-slate-300 flex justify-between">
                <span>OPERATOR USERNAME</span>
                {mode === "register" && (
                  <span className={`text-[10px] ${isUsernameValid ? "text-emerald-400" : "text-slate-500"}`}>
                    3-32 chars (a-z, 0-9, _, -)
                  </span>
                )}
              </label>
              <div className="relative">
                <User className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
                <input
                  type="text"
                  required
                  autoFocus
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. quant_trader_01"
                  className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-white placeholder-slate-600 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 transition-colors"
                />
              </div>
            </div>

            {/* Password Input */}
            <div className="space-y-1.5">
              <label className="text-[11px] font-mono text-slate-300 flex justify-between">
                <span>CRYPTOGRAPHIC PASSPHRASE</span>
                {mode === "register" && (
                  <span className="text-[10px] text-slate-500">Min 8 chars, 1 letter, 1 number</span>
                )}
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full pl-9 pr-10 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-white placeholder-slate-600 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-2.5 text-slate-500 hover:text-slate-300"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Registration Specific Fields */}
            {mode === "register" && (
              <div className="space-y-4 pt-1 animate-fadeIn">
                {/* Confirm Password */}
                <div className="space-y-1.5">
                  <label className="text-[11px] font-mono text-slate-300 flex justify-between">
                    <span>CONFIRM PASSPHRASE</span>
                    {confirmPassword && (
                      <span className={`text-[10px] ${passwordsMatch ? "text-emerald-400" : "text-rose-400"}`}>
                        {passwordsMatch ? "Passwords match" : "Mismatch"}
                      </span>
                    )}
                  </label>
                  <div className="relative">
                    <KeyRound className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
                    <input
                      type={showPassword ? "text" : "password"}
                      required
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="Repeat passphrase"
                      className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-white placeholder-slate-600 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 transition-colors"
                    />
                  </div>
                </div>

                {/* Password Strength Checklist */}
                <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-[10px] font-mono space-y-1">
                  <div className="text-slate-500 uppercase tracking-wider mb-1 font-semibold">Security Matrix:</div>
                  <div className="grid grid-cols-2 gap-1">
                    <div className={`flex items-center gap-1.5 ${hasMinLength ? "text-emerald-400" : "text-slate-500"}`}>
                      <CheckCircle2 className="w-3 h-3" />
                      <span>8+ Characters</span>
                    </div>
                    <div className={`flex items-center gap-1.5 ${hasLetter ? "text-emerald-400" : "text-slate-500"}`}>
                      <CheckCircle2 className="w-3 h-3" />
                      <span>Contains Letter</span>
                    </div>
                    <div className={`flex items-center gap-1.5 ${hasNumber ? "text-emerald-400" : "text-slate-500"}`}>
                      <CheckCircle2 className="w-3 h-3" />
                      <span>Contains Number</span>
                    </div>
                    <div className={`flex items-center gap-1.5 ${passwordsMatch ? "text-emerald-400" : "text-slate-500"}`}>
                      <CheckCircle2 className="w-3 h-3" />
                      <span>Passphrases Match</span>
                    </div>
                  </div>
                </div>

                {/* Role Selection */}
                <div className="space-y-1.5">
                  <label className="text-[11px] font-mono text-slate-300">REQUESTED OPERATIONAL ROLE</label>
                  <div className="grid grid-cols-3 gap-2 text-xs font-mono">
                    <button
                      type="button"
                      onClick={() => setRole("TRADER")}
                      className={`p-2 rounded-lg border text-center transition-all ${
                        role === "TRADER"
                          ? "bg-sky-500/20 text-sky-300 border-sky-500/50 font-semibold"
                          : "bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700"
                      }`}
                    >
                      TRADER
                    </button>
                    <button
                      type="button"
                      onClick={() => setRole("READ_ONLY")}
                      className={`p-2 rounded-lg border text-center transition-all ${
                        role === "READ_ONLY"
                          ? "bg-slate-800 text-white border-slate-600 font-semibold"
                          : "bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700"
                      }`}
                    >
                      VIEWER
                    </button>
                    <button
                      type="button"
                      onClick={() => setRole("ADMIN")}
                      className={`p-2 rounded-lg border text-center transition-all ${
                        role === "ADMIN"
                          ? "bg-purple-500/20 text-purple-300 border-purple-500/50 font-semibold"
                          : "bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700"
                      }`}
                    >
                      ADMIN
                    </button>
                  </div>
                </div>

                {/* Admin Key (If Admin selected) */}
                {role === "ADMIN" && (
                  <div className="space-y-1.5 animate-fadeIn">
                    <label className="text-[11px] font-mono text-purple-300 flex justify-between">
                      <span>ADMIN MASTER REGISTRATION KEY</span>
                      <span className="text-[10px] text-purple-400 font-semibold">REQUIRED</span>
                    </label>
                    <input
                      type="password"
                      required
                      value={adminKey}
                      onChange={(e) => setAdminKey(e.target.value)}
                      placeholder="Enter Admin Master Key"
                      className="w-full px-3 py-2 bg-slate-950 border border-purple-500/40 rounded-lg text-xs font-mono text-purple-200 placeholder-purple-900 focus:outline-none focus:border-purple-500"
                    />
                  </div>
                )}

                {/* Risk & Compliance Disclosure */}
                <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-200/90 text-[11px] space-y-2">
                  <div className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-[10px] text-amber-400">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    <span>Algorithmic Risk Disclosure</span>
                  </div>
                  <p className="text-[10px] leading-relaxed text-amber-200/80">
                    Autonomous Forex and crypto trading involves market volatility and potential financial loss.
                    All executions are deterministically bound to circuit breaker limits and broker truth audits.
                  </p>
                  <label className="flex items-start gap-2 pt-1 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={riskAcknowledged}
                      onChange={(e) => setRiskAcknowledged(e.target.checked)}
                      className="mt-0.5 rounded border-amber-500 text-amber-500 focus:ring-0"
                    />
                    <span className="text-[10px] text-amber-300 font-medium">
                      I accept operational risk boundaries and compliance governance.
                    </span>
                  </label>
                </div>
              </div>
            )}

            {/* Submit Action Button */}
            <button
              type="submit"
              disabled={isSubmitting || (mode === "register" && !canRegister)}
              className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-500 hover:to-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed font-semibold text-xs text-white shadow-lg shadow-sky-600/20 transition-all flex items-center justify-center gap-2 group"
            >
              {isSubmitting ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                  <span>Authenticating...</span>
                </>
              ) : (
                <>
                  <span>{mode === "login" ? "Sign In to Terminal" : "Register Operator Account"}</span>
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                </>
              )}
            </button>
          </form>

          {/* Quick Demo Credentials Bar (For instant testing & dev access) */}
          <div className="pt-2 border-t border-slate-800 space-y-2">
            <div className="text-[10px] font-mono text-slate-500 text-center uppercase tracking-wider">
              Quick Operator Access
            </div>
            <div className="grid grid-cols-3 gap-1.5 text-[10px] font-mono">
              <button
                type="button"
                onClick={() => handleQuickFill("admin", "AdminTrading2026!")}
                className="py-1.5 px-1 rounded bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white transition-colors text-center truncate"
                title="Admin Role: admin / AdminTrading2026!"
              >
                ADMIN
              </button>
              <button
                type="button"
                onClick={() => handleQuickFill("trader", "TraderTrading2026!")}
                className="py-1.5 px-1 rounded bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white transition-colors text-center truncate"
                title="Trader Role: trader / TraderTrading2026!"
              >
                TRADER
              </button>
              <button
                type="button"
                onClick={() => handleQuickFill("viewer", "ViewerTrading2026!")}
                className="py-1.5 px-1 rounded bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white transition-colors text-center truncate"
                title="Viewer Role: viewer / ViewerTrading2026!"
              >
                VIEWER
              </button>
            </div>
          </div>

          {/* Observer Alternative Link */}
          <div className="text-center pt-1">
            <button
              type="button"
              onClick={enterAsGuest}
              className="text-[11px] font-mono text-slate-400 hover:text-sky-400 transition-colors underline underline-offset-4"
            >
              Continue as Observer (Read-Only Telemetry) →
            </button>
          </div>
        </div>
      </div>

      {/* Terminal Footer */}
      <footer className="w-full max-w-5xl py-4 border-t border-slate-900 flex flex-wrap items-center justify-between gap-3 text-[11px] font-mono text-slate-500 z-10">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Backend Gateway Online
          </span>
          <span>·</span>
          <span>Session Lifetime: 12 Hours</span>
        </div>
        <div>
          <span>QuantAI Autonomous Terminal v2.4 · Fail-Closed Architecture</span>
        </div>
      </footer>
    </div>
  );
}
