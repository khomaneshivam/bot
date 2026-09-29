import React from "react";
import { useTrading } from "../../context/TradingContext";
import { NAV_ITEMS } from "../../utils/constants";
import { formatCurrency, formatPnL, getPnLTextColor } from "../../utils/formatters";
import {
  LayoutDashboard,
  CandlestickChart,
  Layers,
  FileText,
  Compass,
  Cpu,
  ShieldAlert,
  Globe,
  Zap,
  Scale,
  Server,
  History,
  RotateCcw,
} from "lucide-react";

const ICON_MAP = {
  LayoutDashboard,
  CandlestickChart,
  Layers,
  FileText,
  Compass,
  Cpu,
  ShieldAlert,
  Globe,
  Zap,
  Scale,
  Server,
  History,
};

export function Sidebar() {
  const { activeView, setActiveView, telemetry, resetCapitalSafe, isSidebarCollapsed } = useTrading();
  const { account, open_positions, circuit_breakers } = telemetry;

  const openCount = open_positions ? open_positions.length : 0;
  const isTripped = circuit_breakers?.tripped;

  return (
    <aside
      className={`${
        isSidebarCollapsed ? "w-16" : "w-60"
      } transition-[width] duration-200 bg-slate-950 border-r border-slate-800 flex flex-col justify-between h-full select-none shrink-0 z-20`}
    >
      {/* Navigation Links */}
      <div className="flex-1 overflow-y-auto py-3 px-2 space-y-1">
        {!isSidebarCollapsed && (
          <div className="px-3 pb-2 mb-1 border-b border-slate-800/80">
            <span className="text-[10px] font-mono font-bold tracking-widest text-slate-500 uppercase">
              Operations Console
            </span>
          </div>
        )}

        {NAV_ITEMS.map((item) => {
          const isActive = activeView === item.id;
          const Icon = ICON_MAP[item.icon] || LayoutDashboard;

          // Special alerts for navigation badges
          let badge = null;
          let badgeClass = "bg-slate-900 text-slate-400 border-slate-800";

          if (item.id === "positions" && openCount > 0) {
            badge = `${openCount} Open`;
            badgeClass = "bg-sky-500/20 text-sky-300 border-sky-500/30";
          } else if (item.id === "risk" && isTripped) {
            badge = "TRIPPED";
            badgeClass = "bg-rose-500/20 text-rose-300 border-rose-500/30 animate-pulse";
          }

          return (
            <button
              key={item.id}
              onClick={() => setActiveView(item.id)}
              title={isSidebarCollapsed ? `${item.label}${badge ? ` (${badge})` : ""}` : undefined}
              className={`w-full flex items-center ${
                isSidebarCollapsed ? "justify-center px-2 py-2.5 relative" : "justify-between px-3 py-2"
              } rounded-lg text-xs font-medium transition-all group ${
                isActive
                  ? "bg-slate-800 text-white font-semibold border border-slate-700 shadow-sm"
                  : "text-slate-400 hover:text-slate-100 hover:bg-slate-900/80"
              }`}
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <Icon
                  className={`w-4 h-4 shrink-0 transition-colors ${
                    isActive ? "text-sky-400" : "text-slate-400 group-hover:text-slate-200"
                  }`}
                />
                {!isSidebarCollapsed && <span className="truncate tracking-wide">{item.label}</span>}
              </div>

              {!isSidebarCollapsed && badge && (
                <span className={`text-[10px] font-mono font-bold px-1.5 py-0.2 rounded border ${badgeClass}`}>
                  {badge}
                </span>
              )}

              {isSidebarCollapsed && badge && (
                <span
                  className={`absolute top-1.5 right-1.5 w-2 h-2 rounded-full ${
                    item.id === "risk" ? "bg-rose-500 animate-ping" : "bg-sky-400"
                  }`}
                />
              )}
            </button>
          );
        })}
      </div>

      {/* Persistent Portfolio Capital Box */}
      {!isSidebarCollapsed ? (
        <div className="p-3 m-2.5 rounded-lg bg-slate-900/90 border border-slate-800 shadow-lg space-y-2.5 shrink-0">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono uppercase text-slate-400 tracking-wider">
              Portfolio Pool
            </span>
            <span
              className={`text-[9px] font-mono px-1.5 py-0.5 rounded font-black uppercase ${
                account?.mode === "live"
                  ? "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                  : "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
              }`}
            >
              {account?.mode || "PAPER"}
            </span>
          </div>

          <div>
            <div className="text-xl font-black font-mono text-white tracking-tight tabular-nums">
              {formatCurrency(account?.equity || 100.0)}
            </div>
            <div className="flex justify-between items-center text-[11px] font-mono mt-0.5">
              <span className="text-slate-400">Balance: {formatCurrency(account?.balance || 100.0)}</span>
              <span className={`font-bold ${getPnLTextColor(account?.realized_pnl || 0)}`}>
                {formatPnL(account?.realized_pnl || 0)}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-1.5 pt-2 border-t border-slate-800 text-[10px] font-mono">
            <div>
              <div className="text-slate-500 uppercase">Win Rate</div>
              <div className="text-white font-bold">{account?.win_rate || 0}%</div>
            </div>
            <div>
              <div className="text-slate-500 uppercase">Positions</div>
              <div className="text-white font-bold">{openCount} active</div>
            </div>
          </div>

          {/* Reset Capital Safe Button */}
          <button
            onClick={resetCapitalSafe}
            className="w-full py-1.5 px-2 rounded text-[11px] font-mono text-slate-400 hover:text-white bg-slate-950 hover:bg-slate-800 border border-slate-800 transition-colors flex items-center justify-center gap-1.5"
            title="Reset paper balance to $100 starting capital"
          >
            <RotateCcw className="w-3 h-3" />
            <span>Reset $100 Pool</span>
          </button>
        </div>
      ) : (
        <div className="p-2 m-1.5 flex flex-col items-center gap-2 border-t border-slate-800">
          <button
            onClick={resetCapitalSafe}
            className="p-2 rounded text-slate-400 hover:text-white bg-slate-900 hover:bg-slate-800 border border-slate-800"
            title="Reset $100 Pool"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      )}
    </aside>
  );
}
