import React, { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import {
  User,
  Shield,
  ShieldCheck,
  Lock,
  Key,
  KeyRound,
  X,
  Copy,
  Check,
  AlertCircle,
  CheckCircle2,
  Clock,
  Server,
  Globe,
  LogOut,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

export function ProfileModal() {
  const { user, isProfileModalOpen, setIsProfileModalOpen, logout, changePassword } = useAuth();

  const [copiedId, setCopiedId] = useState(false);
  const [showPasswordChange, setShowPasswordChange] = useState(false);
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [pwdStatus, setPwdStatus] = useState({ success: null, error: null, isSubmitting: false });

  if (!isProfileModalOpen || !user) return null;

  const handleCopyId = () => {
    if (user.id) {
      navigator.clipboard?.writeText(user.id);
      setCopiedId(true);
      setTimeout(() => setCopiedId(false), 2000);
    }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setPwdStatus({ success: null, error: null, isSubmitting: true });

    if (newPassword.length < 8) {
      setPwdStatus({ success: null, error: "New passphrase must be at least 8 characters long.", isSubmitting: false });
      return;
    }
    if (newPassword !== confirmPassword) {
      setPwdStatus({ success: null, error: "New passphrases do not match.", isSubmitting: false });
      return;
    }

    const res = await changePassword({ oldPassword, newPassword, confirmPassword });
    if (res.success) {
      setPwdStatus({ success: "Passphrase updated successfully.", error: null, isSubmitting: false });
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setTimeout(() => {
        setShowPasswordChange(false);
        setPwdStatus({ success: null, error: null, isSubmitting: false });
      }, 2500);
    } else {
      setPwdStatus({ success: null, error: res.error, isSubmitting: false });
    }
  };

  const role = (user.role || "READ_ONLY").toUpperCase();
  const isAdmin = role === "ADMIN";
  const isTrader = role === "TRADER" || isAdmin;

  const permissionsMatrix = [
    { label: "View Real-time Market Telemetry", allowed: true, required: "READ_ONLY" },
    { label: "Inspect Open Positions & Orders", allowed: true, required: "READ_ONLY" },
    { label: "Observe Risk & Circuit Breakers", allowed: true, required: "READ_ONLY" },
    { label: "Start / Pause Autonomous Engine", allowed: isTrader, required: "TRADER" },
    { label: "Place Manual Trades & Liquidate", allowed: isTrader, required: "TRADER" },
    { label: "Switch Execution Modes (Paper/Live)", allowed: isAdmin, required: "ADMIN" },
    { label: "Reset Portfolio Capital Pool", allowed: isAdmin, required: "ADMIN" },
    { label: "Clear Tripped Circuit Breakers", allowed: isAdmin, required: "ADMIN" },
    { label: "Promote Champion / Challenger ML", allowed: isAdmin, required: "ADMIN" },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4 select-none animate-fadeIn">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="profile-modal-title"
        className="w-full max-w-2xl bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
      >
        {/* Modal Top Bar */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/80">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-sky-500/20 font-bold">
              <User className="w-5 h-5" />
            </div>
            <div>
              <h2 id="profile-modal-title" className="text-sm font-bold text-white font-mono flex items-center gap-2">
                <span>OPERATOR SECURITY PROFILE</span>
                <span className="flex items-center gap-1 text-[10px] text-emerald-400 font-semibold px-1.5 py-0.2 rounded bg-emerald-500/10 border border-emerald-500/30">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  AUTHENTICATED
                </span>
              </h2>
              <p className="text-[11px] font-mono text-slate-400">Cryptographic Identity & Authority Matrix</p>
            </div>
          </div>
          <button
            onClick={() => setIsProfileModalOpen(false)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Body */}
        <div className="p-6 overflow-y-auto space-y-6 text-xs font-mono">
          {/* Identity & Credentials Card */}
          <div className="p-4 rounded-xl bg-slate-950/90 border border-slate-800/80 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/80 pb-3">
              <div>
                <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-semibold">
                  Operator Identity
                </span>
                <div className="text-lg font-black text-white tracking-tight flex items-center gap-2">
                  <span>{user.username}</span>
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded border uppercase font-extrabold tracking-wider ${
                      isAdmin
                        ? "bg-purple-500/20 text-purple-300 border-purple-500/40"
                        : isTrader
                        ? "bg-sky-500/20 text-sky-300 border-sky-500/40"
                        : "bg-slate-800 text-slate-300 border-slate-700"
                    }`}
                  >
                    {role}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-[11px] text-slate-400 font-mono">ID: {user.id}</span>
                <button
                  onClick={handleCopyId}
                  className="p-1 rounded bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white border border-slate-800 transition-colors"
                  title="Copy User ID"
                >
                  {copiedId ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
            </div>

            {/* Metadata Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-[11px]">
              <div>
                <span className="text-slate-500 block text-[10px] uppercase font-semibold">Origin IP</span>
                <span className="text-slate-200 flex items-center gap-1 mt-0.5">
                  <Globe className="w-3.5 h-3.5 text-sky-400" />
                  {user.client_ip || "127.0.0.1"}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px] uppercase font-semibold">Active Sessions</span>
                <span className="text-slate-200 flex items-center gap-1 mt-0.5">
                  <Server className="w-3.5 h-3.5 text-emerald-400" />
                  {user.active_sessions_count || 1} Session
                </span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px] uppercase font-semibold">Registered At</span>
                <span className="text-slate-200 flex items-center gap-1 mt-0.5">
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  {user.created_at || "2026-09-27"}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px] uppercase font-semibold">Last Authenticated</span>
                <span className="text-slate-200 flex items-center gap-1 mt-0.5">
                  <Clock className="w-3.5 h-3.5 text-amber-400" />
                  {user.last_login || "Active Now"}
                </span>
              </div>
            </div>
          </div>

          {/* Cryptographic Standards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[11px]">
            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 flex items-start gap-2.5">
              <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <div className="text-white font-bold">Argon2id Memory-Hard Hashing</div>
                <div className="text-[10px] text-slate-400 mt-0.5">
                  Protects passphrases against GPU/ASIC brute force attacks with cryptographic salts.
                </div>
              </div>
            </div>
            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 flex items-start gap-2.5">
              <Lock className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
              <div>
                <div className="text-white font-bold">HMAC-SHA256 Signed Bearer Tokens</div>
                <div className="text-[10px] text-slate-400 mt-0.5">
                  12-hour session lifetime with database-level revocation on logout.
                </div>
              </div>
            </div>
          </div>

          {/* RBAC Capability Matrix */}
          <div className="p-4 rounded-xl bg-slate-950/90 border border-slate-800/80 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
              <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-sky-400" />
                <span>RBAC Authority & Control Permissions</span>
              </span>
              <span className="text-[10px] text-slate-500 font-mono">Tier: {role}</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
              {permissionsMatrix.map((item, idx) => (
                <div
                  key={idx}
                  className={`p-2 rounded-lg border flex items-center justify-between ${
                    item.allowed
                      ? "bg-slate-900/60 border-slate-800 text-slate-200"
                      : "bg-slate-950/40 border-slate-900 text-slate-500 opacity-60"
                  }`}
                >
                  <span className="truncate">{item.label}</span>
                  <span
                    className={`text-[9px] px-1.5 py-0.2 rounded font-mono font-bold uppercase shrink-0 ${
                      item.allowed
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                        : "bg-slate-900 text-slate-500 border border-slate-800"
                    }`}
                  >
                    {item.allowed ? "ALLOWED" : "LOCKED"}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Change Passphrase Accordion */}
          <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-950/80">
            <button
              type="button"
              onClick={() => setShowPasswordChange(!showPasswordChange)}
              className="w-full p-3.5 flex items-center justify-between text-left hover:bg-slate-900/80 transition-colors"
            >
              <div className="flex items-center gap-2 text-slate-200 font-bold">
                <Key className="w-4 h-4 text-amber-400" />
                <span>Change Cryptographic Passphrase</span>
              </div>
              {showPasswordChange ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
            </button>

            {showPasswordChange && (
              <form onSubmit={handlePasswordSubmit} className="p-4 pt-1 border-t border-slate-800/80 space-y-3 animate-fadeIn">
                {pwdStatus.error && (
                  <div className="p-2.5 rounded bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                    <span>{pwdStatus.error}</span>
                  </div>
                )}
                {pwdStatus.success && (
                  <div className="p-2.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>{pwdStatus.success}</span>
                  </div>
                )}

                <div className="space-y-1">
                  <label className="text-[10px] text-slate-400 uppercase">Current Passphrase</label>
                  <input
                    type="password"
                    required
                    value={oldPassword}
                    onChange={(e) => setOldPassword(e.target.value)}
                    placeholder="Enter existing passphrase"
                    className="w-full px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-white font-mono focus:outline-none focus:border-sky-500"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-[10px] text-slate-400 uppercase">New Passphrase (Min 8 chars)</label>
                    <input
                      type="password"
                      required
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="New strong passphrase"
                      className="w-full px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-white font-mono focus:outline-none focus:border-sky-500"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] text-slate-400 uppercase">Confirm Passphrase</label>
                    <input
                      type="password"
                      required
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="Repeat new passphrase"
                      className="w-full px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-white font-mono focus:outline-none focus:border-sky-500"
                    />
                  </div>
                </div>

                <div className="pt-1 flex justify-end">
                  <button
                    type="submit"
                    disabled={pwdStatus.isSubmitting}
                    className="px-4 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs shadow-md shadow-amber-600/20 transition-all flex items-center gap-1.5 disabled:opacity-50"
                  >
                    <KeyRound className="w-3.5 h-3.5" />
                    <span>{pwdStatus.isSubmitting ? "Updating..." : "Update Passphrase"}</span>
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 border-t border-slate-800 flex items-center justify-between bg-slate-950/80">
          <button
            onClick={() => {
              setIsProfileModalOpen(false);
              logout();
            }}
            className="px-3 py-2 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 hover:text-white border border-rose-500/30 transition-all flex items-center gap-1.5 font-bold"
          >
            <LogOut className="w-4 h-4" />
            <span>Sign Out & Terminate Session</span>
          </button>

          <button
            onClick={() => setIsProfileModalOpen(false)}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white font-bold transition-colors"
          >
            Close Profile
          </button>
        </div>
      </div>
    </div>
  );
}
