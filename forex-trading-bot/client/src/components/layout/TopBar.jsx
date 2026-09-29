import React from "react";
import { useTrading } from "../../context/TradingContext";
import { useAuth } from "../../context/AuthContext";
import { EXECUTION_MODES } from "../../utils/constants";
import { DataFreshness } from "../common/DataFreshness";
import { Play, Pause, AlertOctagon, User as UserIcon, Shield, LogOut, LogIn, PanelLeft } from "lucide-react";

export function TopBar() {
  const {
    telemetry,
    isConnected,
    lastMessageTime,
    latencyMs,
    switchModeSafe,
    switchSymbol,
    toggleBotSafe,
    emergencyKillSafe,
    toggleSidebar,
  } = useTrading();

  const { user, isAuthenticated, isGuest, logout, setIsLoginModalOpen, setIsProfileModalOpen } = useAuth();

  const { symbol, is_running, account, broker_connected, feed_fresh, circuit_breakers } = telemetry;
  const currentModeKey = (account?.mode || "paper").toLowerCase();

  // Find matching mode or fallback to PAPER
  const activeMode = Object.values(EXECUTION_MODES).find(
    (m) => m.key === currentModeKey || m.shortLabel.toLowerCase() === currentModeKey
  ) || EXECUTION_MODES.PAPER;

  const isLive = activeMode.isLive;

  return (
    <header className="h-16 px-4 sm:px-6 bg-slate-950 border-b border-slate-800 flex items-center justify-between gap-4 select-none shrink-0 z-30">
      {/* Left: Brand, Environment & Mode */}
      <div className="flex items-center gap-2.5">
        <button
          onClick={toggleSidebar}
          aria-label="Toggle Navigation Sidebar"
          className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white border border-slate-800 transition-colors"
          title="Toggle Navigation Sidebar"
        >
          <PanelLeft className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-sky-600 flex items-center justify-center font-black text-white text-sm tracking-wider shadow-sm">
            Q
          </div>
          <div className="hidden sm:block">
            <span className="font-extrabold tracking-wider text-sm text-white">
              QUANT<span className="text-sky-400">AI</span>
            </span>
            <span className="text-[10px] font-mono text-slate-400 ml-1.5 px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800">
              PRO TERMINAL
            </span>
          </div>
        </div>

        {/* HIGH-VISIBILITY EXECUTION MODE BADGE */}
        <div className="flex items-center gap-1.5 ml-2">
          <div
            className={`px-3 py-1.5 rounded-lg border font-mono font-black text-xs tracking-wider flex items-center gap-2 shadow-sm ${
              isLive
                ? "bg-rose-500/20 text-rose-300 border-rose-500 animate-pulse"
                : activeMode.variant === "cyan"
                ? "bg-cyan-500/15 text-cyan-300 border-cyan-500/40"
                : "bg-emerald-500/15 text-emerald-300 border-emerald-500/40"
            }`}
            title={activeMode.description}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isLive ? "bg-rose-500 animate-ping" : activeMode.variant === "cyan" ? "bg-cyan-400" : "bg-emerald-400"
              }`}
            />
            <span>MODE: {activeMode.label}</span>
          </div>

          {/* Quick Mode Switch Dropdown */}
          <select
            value={activeMode.key}
            onChange={(e) => switchModeSafe(e.target.value)}
            className="bg-slate-900 border border-slate-700 text-slate-300 text-xs font-mono rounded px-2 py-1 focus:outline-none focus:border-sky-500"
            title="Switch execution engine mode"
          >
            <option value="paper">Switch to Paper Trading</option>
            <option value="demo">Switch to MT5 Demo</option>
            <option value="live">Switch to MT5 LIVE Real Capital</option>
          </select>
        </div>
      </div>

      {/* Center: Market Symbol & Telemetry Freshness */}
      <div className="hidden lg:flex items-center gap-3">
        {/* Symbol Selector */}
        <div className="flex items-center gap-2 bg-slate-900/80 px-2.5 py-1 rounded-lg border border-slate-800 text-xs font-mono">
          <span className="text-slate-400">ASSET:</span>
          <select
            value={symbol}
            onChange={(e) => switchSymbol(e.target.value)}
            className="bg-transparent text-white font-bold focus:outline-none cursor-pointer"
          >
            <optgroup label="Forex Major Currencies">
              <option value="EURUSD">EUR/USD (Euro / US Dollar)</option>
              <option value="GBPUSD">GBP/USD (British Pound)</option>
              <option value="USDJPY">USD/JPY (US Dollar / Yen)</option>
              <option value="USDCHF">USD/CHF (US Dollar / Swiss Franc)</option>
              <option value="AUDUSD">AUD/USD (Australian Dollar)</option>
            </optgroup>
            <optgroup label="Precious Metals">
              <option value="XAUUSD">XAU/USD (Spot Gold)</option>
            </optgroup>
            <optgroup label="Crypto Assets">
              <option value="BTCUSDT">BTC/USDT (Bitcoin)</option>
              <option value="ETHUSDT">ETH/USDT (Ethereum)</option>
              <option value="SOLUSDT">SOL/USDT (Solana)</option>
            </optgroup>
          </select>
          <span className="text-[10px] text-slate-400 px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700">
            5M
          </span>
        </div>

        {/* Data Freshness Indicator */}
        <DataFreshness
          lastUpdated={lastMessageTime}
          isConnected={isConnected}
          isStale={!feed_fresh}
        />

        {latencyMs !== null && (
          <span className="text-[11px] font-mono text-slate-400">
            {latencyMs}ms
          </span>
        )}
      </div>

      {/* Right: Operational Controls & User RBAC */}
      <div className="flex items-center gap-2.5">
        {/* Autonomous Bot Toggle */}
        <button
          onClick={toggleBotSafe}
          className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold flex items-center gap-1.5 border transition-all ${
            is_running
              ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/40 hover:bg-emerald-500/25"
              : "bg-amber-500/15 text-amber-300 border-amber-500/40 hover:bg-amber-500/25"
          }`}
          title={is_running ? "Pause autonomous trading loop" : "Start autonomous trading loop"}
        >
          {is_running ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
          <span className="hidden sm:inline">{is_running ? "ENGINE: RUNNING" : "ENGINE: PAUSED"}</span>
        </button>

        {/* Emergency Kill Switch */}
        <button
          onClick={emergencyKillSafe}
          className="px-3 py-1.5 rounded-lg text-xs font-mono font-bold bg-rose-600/20 text-rose-300 border border-rose-500/40 hover:bg-rose-600 hover:text-white transition-all flex items-center gap-1.5 shadow-sm"
          title="Instant Emergency Halt: Liquidate positions and trip circuit breaker"
        >
          <AlertOctagon className="w-3.5 h-3.5" />
          <span className="hidden md:inline">KILL SWITCH</span>
        </button>

        {/* User RBAC / Login Status */}
        <div className="border-l border-slate-800 pl-2.5 flex items-center gap-2">
          {isAuthenticated ? (
            <div className="flex items-center gap-2">
              <button
                onClick={() => setIsProfileModalOpen(true)}
                title="View Operator Security Profile & Credentials"
                className="hidden sm:flex flex-col text-right px-2 py-1 rounded hover:bg-slate-900 border border-transparent hover:border-slate-800 transition-colors group cursor-pointer"
              >
                <span className="text-xs font-bold font-mono text-white group-hover:text-sky-300 leading-tight flex items-center gap-1 justify-end">
                  <UserIcon className="w-3 h-3 text-sky-400" />
                  <span>{user.username}</span>
                </span>
                <span className="text-[9px] font-mono text-sky-400 uppercase tracking-wider font-semibold">
                  {user.role}
                </span>
              </button>
              <button
                onClick={() => setIsProfileModalOpen(true)}
                title="View Operator Profile"
                className="sm:hidden p-1.5 rounded hover:bg-slate-800 text-sky-400 hover:text-white transition-colors"
              >
                <UserIcon className="w-4 h-4" />
              </button>
              <button
                onClick={logout}
                title="Sign out of terminal"
                className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-rose-400 transition-colors"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              {isGuest && (
                <div className="hidden sm:flex flex-col text-right">
                  <span className="text-xs font-bold font-mono text-slate-300 leading-tight">
                    Observer
                  </span>
                  <span className="text-[9px] font-mono text-amber-400 uppercase tracking-wider">
                    READ ONLY
                  </span>
                </div>
              )}
              <button
                onClick={() => setIsLoginModalOpen(true)}
                className="px-2.5 py-1 text-xs font-mono font-medium rounded bg-sky-600/20 hover:bg-sky-600/30 border border-sky-500/40 text-sky-300 hover:text-white flex items-center gap-1.5 transition-colors"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>Sign In / Register</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
