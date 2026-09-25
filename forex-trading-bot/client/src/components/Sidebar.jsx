/**
 * QuantAI Terminal - Institutional Navigation Sidebar
 * 20+ Year Hedge Fund View Routing & $100 Portfolio Capital Monitor
 */

import React from "react";
import { useTrading } from "../context/TradingContext";
import { formatCurrency, formatPnL, getPnLColorClass } from "../utils/formatters";

export function Sidebar() {
  const { activeView, setActiveView, telemetry, resetCapital } = useTrading();
  const { account, open_positions, ml_stats, dxy_proxy, news, psychology } = telemetry;

  const totalTrades = account?.total_trades || 0;
  const openCount = open_positions ? open_positions.length : 0;
  const vetoCount = ml_stats ? ml_stats.vetoed_trades_count || 0 : 0;
  const goldScore = news?.gold_sentiment_score || 75;
  const disciplineScore = psychology?.discipline_index || 98.5;

  const navItems = [
    {
      id: "terminal",
      label: "Live Terminal",
      icon: "🖥️",
      badge: `${openCount} Open`,
      badgeHighlight: openCount > 0,
    },
    {
      id: "ledger",
      label: "All Trades Ledger",
      icon: "📜",
      badge: `${totalTrades} Trades`,
      badgeHighlight: false,
    },
    {
      id: "scanner",
      label: "1-Min Multi-Pair Scanner",
      icon: "⚡",
      badge: "9 Pairs",
      badgeHighlight: false,
    },
    {
      id: "news",
      label: "Gold & Macro News",
      icon: "📰",
      badge: `Gold ${goldScore}%`,
      badgeHighlight: true,
      badgeColor: "bg-amber-500/20 text-amber-400 border border-amber-500/30",
    },
    {
      id: "psychology",
      label: "Trader Psychology & Tilt",
      icon: "🧠",
      badge: `${disciplineScore}%`,
      badgeHighlight: true,
      badgeColor: "bg-purple-500/20 text-purple-400 border border-purple-500/30",
    },
    {
      id: "ai-studio",
      label: "AI Neural Retrain",
      icon: "🤖",
      badge: `${vetoCount} Vetoes`,
      badgeHighlight: vetoCount > 0,
    },
    {
      id: "macro",
      label: "Macro & DXY Matrix",
      icon: "🌐",
      badge: `DXY ${Number(dxy_proxy || 101.4).toFixed(1)}`,
      badgeHighlight: false,
    },
  ];

  return (
    <aside className="w-64 bg-obsidian-950 border-r border-slate-800/80 flex flex-col justify-between h-screen select-none z-20">
      {/* Brand Header */}
      <div>
        <div
          className="p-5 border-b border-slate-800/80 flex items-center gap-3 cursor-pointer group"
          onClick={() => setActiveView("terminal")}
        >
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 via-cyan-400 to-emerald-400 flex items-center justify-center shadow-lg shadow-cyan-500/20 group-hover:scale-105 transition-transform">
            <span className="text-obsidian-950 font-black text-xl">Q</span>
          </div>
          <div>
            <div className="text-base font-extrabold tracking-wider text-white flex items-center gap-1.5">
              QUANT<span className="text-cyan-400">AI</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded font-mono font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                HEDGE FUND
              </span>
            </div>
            <div className="text-[10px] text-slate-400 font-mono tracking-tight">
              20+ Yr Quant System
            </div>
          </div>
        </div>

        {/* Navigation List */}
        <nav className="p-3 space-y-1.5 overflow-y-auto max-h-[calc(100vh-270px)]">
          {navItems.map((item) => {
            const isActive = activeView === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveView(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition-all group ${
                  isActive
                    ? "bg-slate-800 text-white font-semibold shadow-inner border border-slate-700/80"
                    : "text-slate-400 hover:text-slate-100 hover:bg-obsidian-900"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <span className="text-base group-hover:scale-110 transition-transform">{item.icon}</span>
                  <span className="tracking-wide text-left">{item.label}</span>
                </div>

                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded-full ${
                    item.badgeColor ||
                    (isActive
                      ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30"
                      : "bg-obsidian-900 text-slate-400 border border-slate-800")
                  }`}
                >
                  {item.badge}
                </span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Portfolio Capital & Account Balance Box */}
      <div className="p-4 m-3 rounded-xl bg-gradient-to-b from-obsidian-900 to-obsidian-950 border border-slate-800/90 shadow-xl space-y-3">
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-400 font-mono text-[11px] uppercase tracking-wider">Starting $100 Pool</span>
          <span
            className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase ${
              account?.mode === "live"
                ? "bg-rose-500/20 text-rose-400 border border-rose-500/40"
                : account?.mode === "demo"
                ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/40"
                : "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
            }`}
          >
            {account?.mode || "PAPER"}
          </span>
        </div>

        {/* Live Balance with Pip/Loss Deduction */}
        <div>
          <div className="text-2xl font-black font-mono text-white tracking-tight">
            {formatCurrency(account?.balance || 100.0)}
          </div>
          <div className="flex justify-between items-center text-[11px] font-mono mt-1 text-slate-400">
            <span>Equity: <strong className="text-slate-200">{formatCurrency(account?.equity || 100.0)}</strong></span>
            <span className={getPnLColorClass(account?.realized_pnl || 0.0)}>
              {formatPnL(account?.realized_pnl || 0.0)}
            </span>
          </div>
        </div>

        {/* Win Rate & Total Trades */}
        <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800/80 text-[10px] font-mono">
          <div>
            <div className="text-slate-500 uppercase">Win Rate</div>
            <div className="text-white font-bold text-xs">{account?.win_rate || 0}%</div>
          </div>
          <div>
            <div className="text-slate-500 uppercase">Total Trades</div>
            <div className="text-white font-bold text-xs">{totalTrades}</div>
          </div>
        </div>

        {/* Reset Capital Button */}
        <button
          onClick={resetCapital}
          className="w-full py-2 px-3 rounded-lg text-xs font-mono font-medium text-slate-400 bg-obsidian-950 hover:bg-slate-800 hover:text-white border border-slate-800 transition-colors flex items-center justify-center gap-1.5"
          title="Reset portfolio back to clean $100 starting capital"
        >
          <span>↺</span>
          <span>Reset $100 Capital</span>
        </button>
      </div>
    </aside>
  );
}
