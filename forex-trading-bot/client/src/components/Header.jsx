/**
 * QuantAI Terminal - Top Navigation & Control Header
 * Institutional Real-time Telemetry, Asset Selector, and Execution Controls
 */

import React from "react";
import { useTrading } from "../context/TradingContext";

export function Header() {
  const {
    connectionStatus,
    telemetry,
    switchMode,
    switchSymbol,
    toggleBot,
    emergencyKill,
  } = useTrading();

  const { symbol, is_running, account, dxy_proxy, dxy_trend, news, psychology } = telemetry;
  const currentMode = account?.mode || "paper";
  const isOnline = connectionStatus.includes("ONLINE");
  const tiltActive = psychology?.tilt_shield_active;

  return (
    <header className="h-16 px-6 bg-obsidian-950/90 backdrop-blur-md border-b border-slate-800/80 flex items-center justify-between gap-4 z-10 shrink-0">
      {/* Left: Stream Status & DXY Macro Ticker */}
      <div className="flex items-center gap-3">
        {/* Connection Pulse */}
        <div
          className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-mono font-bold border transition-colors ${
            isOnline
              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
              : "bg-rose-500/10 text-rose-400 border-rose-500/30"
          }`}
        >
          <span className={`w-2 h-2 rounded-full ${isOnline ? "bg-emerald-400 animate-pulse" : "bg-rose-500"}`} />
          <span>{connectionStatus}</span>
        </div>

        {/* DXY Dollar Index Micro Ticker */}
        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-obsidian-900 border border-slate-800 text-xs font-mono">
          <span className="text-slate-400">DXY:</span>
          <span className="text-white font-bold">{Number(dxy_proxy || 101.42).toFixed(2)}</span>
          <span
            className={`text-[10px] font-bold ${
              dxy_trend?.includes("BULLISH")
                ? "text-emerald-400"
                : dxy_trend?.includes("BEARISH")
                ? "text-rose-400"
                : "text-slate-400"
            }`}
          >
            {(dxy_trend || "NEUTRAL").replace(/_/g, " ")}
          </span>
        </div>

        {/* Cognitive & News Shield Badges */}
        {tiltActive && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-rose-500/20 text-rose-400 border border-rose-500/40 text-xs font-mono animate-pulse">
            <span>🛡️ TILT SHIELD ARMED</span>
          </div>
        )}
      </div>

      {/* Center: Paper / Demo / Live Mode Selector */}
      <div className="flex items-center bg-obsidian-900 p-1 rounded-xl border border-slate-800 text-xs">
        <button
          onClick={() => switchMode("paper")}
          className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
            currentMode === "paper"
              ? "bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/30 shadow-sm"
              : "text-slate-400 hover:text-white"
          }`}
          title="Paper Trading ($100 Starting Balance with Loss Deduction)"
        >
          🟢 Paper ($100)
        </button>

        <button
          onClick={() => switchMode("demo")}
          className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
            currentMode === "demo"
              ? "bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/30 shadow-sm"
              : "text-slate-400 hover:text-white"
          }`}
          title="Broker Demo / Testnet API"
        >
          🔵 Demo MT5
        </button>

        <button
          onClick={() => switchMode("live")}
          className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
            currentMode === "live"
              ? "bg-rose-500/20 text-rose-300 font-bold border border-rose-500/30 shadow-sm"
              : "text-slate-400 hover:text-white"
          }`}
          title="Live Account Execution"
        >
          🔴 Live
        </button>
      </div>

      {/* Right: Asset Selector & Engine Controls */}
      <div className="flex items-center gap-3">
        {/* Asset Selector Dropdown */}
        <div className="flex items-center gap-2">
          <label htmlFor="symbol-select" className="text-xs font-mono text-slate-400 hidden md:inline">
            ASSET:
          </label>
          <select
            id="symbol-select"
            value={symbol}
            onChange={(e) => switchSymbol(e.target.value)}
            className="bg-obsidian-900 border border-slate-700 text-white text-xs font-mono rounded-lg px-3 py-1.5 focus:outline-none focus:border-cyan-400"
          >
            <optgroup label="Forex Major Currencies">
              <option value="EURUSD">EUR/USD (Euro / Dollar)</option>
              <option value="GBPUSD">GBP/USD (British Pound)</option>
              <option value="USDJPY">USD/JPY (Dollar / Yen)</option>
              <option value="USDCHF">USD/CHF (Dollar / Swiss Franc)</option>
              <option value="AUDUSD">AUD/USD (Australian Dollar)</option>
            </optgroup>
            <optgroup label="Commodities & Metals">
              <option value="XAUUSD">XAU/USD (Spot Gold)</option>
            </optgroup>
            <optgroup label="Crypto Assets">
              <option value="BTCUSDT">BTC/USDT (Bitcoin)</option>
              <option value="ETHUSDT">ETH/USDT (Ethereum)</option>
              <option value="SOLUSDT">SOL/USDT (Solana)</option>
            </optgroup>
          </select>
        </div>

        {/* Autonomous Bot Toggle */}
        <button
          onClick={toggleBot}
          className={`px-4 py-1.5 rounded-lg text-xs font-bold font-mono transition-all flex items-center gap-1.5 border ${
            is_running
              ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40 shadow-lg shadow-emerald-500/10 animate-pulse-subtle"
              : "bg-slate-800 text-slate-400 border-slate-700 hover:text-white"
          }`}
        >
          <span>⚡</span>
          <span>{is_running ? "BOT: ACTIVE" : "BOT: PAUSED"}</span>
        </button>

        {/* Emergency Kill Switch */}
        <button
          onClick={emergencyKill}
          className="px-3 py-1.5 rounded-lg text-xs font-bold font-mono bg-rose-600/20 text-rose-300 border border-rose-500/40 hover:bg-rose-600 hover:text-white transition-all flex items-center gap-1.5 shadow-lg shadow-rose-600/10"
          title="Instant circuit breaker: Close all open positions and freeze execution"
        >
          <span>🛑</span>
          <span className="hidden sm:inline">KILL SWITCH</span>
        </button>
      </div>
    </header>
  );
}
