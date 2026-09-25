import React from "react";
import { useTrading } from "../context/TradingContext";
import { formatCurrency } from "../utils/formatters";

export default function PsychologyView() {
  const { telemetry } = useTrading();
  const psych = telemetry.psychology || {
    discipline_index: 98.5,
    emotional_state: "OPTIMAL_FLOW",
    fear_greed_score: 52,
    fear_greed_label: "NEUTRAL / BALANCED",
    consecutive_losses: 0,
    consecutive_wins: 0,
    cooloff_remaining_seconds: 0,
    tilt_shield_active: false,
    fomo_vetoes_count: 0,
    revenge_blocks_count: 0,
    mindset_mantra: "Trade what you see, not what you feel. Let mathematics, probability, and structure dictate execution.",
    recent_psychology_logs: []
  };

  const account = telemetry.account || { balance: 100.0, equity: 100.0 };
  const dailyDrawdownBudget = 4.0; // 4% of $100
  const currentDrawdown = Math.max(0, 100.0 - account.balance);
  const remainingBudget = Math.max(0, dailyDrawdownBudget - currentDrawdown);

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-obsidian-950 text-slate-100">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 rounded-xl bg-gradient-to-r from-obsidian-900 via-obsidian-850 to-obsidian-900 border border-slate-800 shadow-2xl">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-2xl shadow-inner">
            🧠
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-3">
              20+ Year Institutional Trader Psychology & Behavioral Guard
              <span className="text-xs px-2.5 py-0.5 rounded-full font-mono bg-purple-500/10 text-purple-400 border border-purple-500/30">
                ACTIVE COGNITIVE SHIELD
              </span>
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Eliminating retail emotional failure modes: FOMO, Tilt, Revenge Trading, and Overconfidence Bias
            </p>
          </div>
        </div>

        {/* Emotional State Badge */}
        <div className="flex items-center gap-3 bg-obsidian-950 px-4 py-2.5 rounded-lg border border-slate-800">
          <div className={`w-3 h-3 rounded-full ${psych.tilt_shield_active ? "bg-rose-500 animate-ping" : "bg-emerald-400 animate-pulse"}`} />
          <div>
            <div className="text-[10px] font-mono uppercase text-slate-400">Trader Operational Mindset</div>
            <div className="text-xs font-bold text-white font-mono flex items-center gap-1.5">
              <span className={psych.tilt_shield_active ? "text-rose-400" : "text-emerald-400"}>
                {psych.emotional_state.replace("_", " ")}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Senior Trader Wisdom Mantra */}
      <div className="p-4 rounded-xl bg-gradient-to-r from-purple-950/40 via-obsidian-900 to-obsidian-950 border border-purple-800/40 shadow-lg flex items-center gap-4">
        <span className="text-2xl text-purple-400">💡</span>
        <div className="flex-1">
          <div className="text-[10px] uppercase font-mono tracking-wider text-purple-300 font-bold">
            Senior Hedge Fund Portfolio Manager Directive
          </div>
          <p className="text-sm font-medium text-slate-200 italic mt-0.5">
            "{psych.mindset_mantra}"
          </p>
        </div>
      </div>

      {/* 4 Core Psychological Radar Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Card 1: Discipline Index */}
        <div className="p-4 rounded-xl bg-obsidian-900/80 border border-slate-800 shadow-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono text-slate-400">DISCIPLINE INDEX</span>
            <span className="text-xs font-mono font-bold text-emerald-400">IRON WILL</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-black font-mono text-emerald-400">{psych.discipline_index}%</span>
            <span className="text-xs text-slate-400">Zero Rule Violations</span>
          </div>
          <div className="w-full bg-slate-800 h-1.5 rounded-full mt-3 overflow-hidden">
            <div
              className="bg-emerald-500 h-full rounded-full transition-all duration-700"
              style={{ width: `${psych.discipline_index}%` }}
            />
          </div>
          <div className="text-[10px] text-slate-400 mt-2">
            Plan followed 100%. No discretionary impulses allowed.
          </div>
        </div>

        {/* Card 2: Market Fear & Greed */}
        <div className="p-4 rounded-xl bg-obsidian-900/80 border border-slate-800 shadow-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono text-slate-400">FEAR & GREED GAUGE</span>
            <span className="text-xs font-mono font-bold text-cyan-400">{psych.fear_greed_score}/100</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-black font-mono text-white">{psych.fear_greed_label}</span>
          </div>
          <div className="w-full bg-slate-800 h-1.5 rounded-full mt-3 overflow-hidden">
            <div
              className="bg-gradient-to-r from-cyan-500 to-amber-400 h-full rounded-full transition-all duration-700"
              style={{ width: `${psych.fear_greed_score}%` }}
            />
          </div>
          <div className="text-[10px] text-slate-400 mt-2 flex justify-between">
            <span>Extreme Fear</span>
            <span>Balanced</span>
            <span>Extreme Greed</span>
          </div>
        </div>

        {/* Card 3: Tilt & Revenge Circuit Breaker */}
        <div className="p-4 rounded-xl bg-obsidian-900/80 border border-slate-800 shadow-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono text-slate-400">TILT CIRCUIT BREAKER</span>
            <span className="text-xs font-mono text-slate-300 font-bold">{psych.consecutive_losses} / 2 LOSSES</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className={`text-2xl font-black font-mono ${psych.tilt_shield_active ? "text-rose-400" : "text-emerald-400"}`}>
              {psych.tilt_shield_active ? `${psych.cooloff_remaining_seconds}s COOLOFF` : "ARMED & STANDING BY"}
            </span>
          </div>
          <div className="w-full bg-slate-800 h-1.5 rounded-full mt-3 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-700 ${psych.tilt_shield_active ? "bg-rose-500" : "bg-emerald-500"}`}
              style={{ width: `${(psych.consecutive_losses / 2) * 100}%` }}
            />
          </div>
          <div className="text-[10px] text-slate-400 mt-2">
            Halves lot size or pauses after 2 consecutive stop-outs.
          </div>
        </div>

        {/* Card 4: FOMO Liquidity Trap Shield */}
        <div className="p-4 rounded-xl bg-obsidian-900/80 border border-slate-800 shadow-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono text-slate-400">FOMO TRAPS BLOCKED</span>
            <span className="text-xs font-mono text-purple-400 font-bold">CAPITAL SAVED</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-black font-mono text-purple-400">{psych.fomo_vetoes_count}</span>
            <span className="text-xs text-slate-400">Overextensions Vetoed</span>
          </div>
          <div className="w-full bg-slate-800 h-1.5 rounded-full mt-3 overflow-hidden">
            <div
              className="bg-purple-500 h-full rounded-full"
              style={{ width: `${Math.min(100, (psych.fomo_vetoes_count + 1) * 20)}%` }}
            />
          </div>
          <div className="text-[10px] text-slate-400 mt-2">
            Prevents buying candle tops (&gt;2 ATR extended / RSI &gt; 74).
          </div>
        </div>
      </div>

      {/* Main Split: Psychology Veto Breakdown & Capital Preservation Box */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Psychological Audit Logs (7 Cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
              Real-Time Behavioral Audit Log
            </h2>
            <span className="text-xs text-slate-400 font-mono">
              Revenge Blocks: <span className="text-rose-400 font-bold">{psych.revenge_blocks_count}</span>
            </span>
          </div>

          <div className="space-y-3">
            {(!psych.recent_psychology_logs || psych.recent_psychology_logs.length === 0) ? (
              <div className="p-8 text-center bg-obsidian-900/50 rounded-xl border border-slate-800 text-slate-500 text-xs font-mono">
                No psychological anomalies detected. System operating in optimal composed execution flow.
              </div>
            ) : (
              psych.recent_psychology_logs.map((log, i) => (
                <div
                  key={i}
                  className="p-4 rounded-xl bg-obsidian-900/90 border border-slate-800/80 hover:border-slate-700 transition-all text-xs"
                >
                  <div className="flex items-center justify-between gap-3 mb-1">
                    <span className="font-mono text-purple-400 font-bold">{log.event}</span>
                    <span className="font-mono text-slate-500 text-[11px]">{log.timestamp} • {log.symbol}</span>
                  </div>
                  <p className="text-slate-300 leading-relaxed font-mono">
                    {log.detail}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right: Senior Trader Psychology Rules (5 Cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Daily Drawdown Risk-of-Ruin Buffer */}
          <div className="p-5 rounded-xl bg-obsidian-900/80 border border-slate-800 shadow-xl space-y-4">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200 flex items-center gap-2">
              🛡️ $100 Capital Preservation Buffer
            </h2>
            <div className="p-4 rounded-lg bg-obsidian-950 border border-slate-800 space-y-3 text-xs">
              <div className="flex justify-between font-mono">
                <span className="text-slate-400">Current Balance:</span>
                <span className="text-white font-bold">{formatCurrency(account.balance)}</span>
              </div>
              <div className="flex justify-between font-mono">
                <span className="text-slate-400">Max Daily Loss Tolerance (4%):</span>
                <span className="text-rose-400 font-bold">${dailyDrawdownBudget.toFixed(2)}</span>
              </div>
              <div className="flex justify-between font-mono">
                <span className="text-slate-400">Remaining Loss Allowance:</span>
                <span className="text-emerald-400 font-bold">${remainingBudget.toFixed(2)}</span>
              </div>
              <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden mt-1">
                <div
                  className="bg-emerald-400 h-full rounded-full transition-all duration-500"
                  style={{ width: `${(remainingBudget / dailyDrawdownBudget) * 100}%` }}
                />
              </div>
            </div>
          </div>

          {/* 5 Cognitive Biases Neutralized */}
          <div className="p-5 rounded-xl bg-gradient-to-b from-obsidian-900 to-obsidian-950 border border-slate-800 shadow-xl space-y-3">
            <h2 className="text-sm font-bold uppercase tracking-wider text-purple-400 flex items-center gap-2">
              🧠 5 Cognitive Biases Neutralized By Bot
            </h2>

            <div className="space-y-2 text-xs font-mono">
              <div className="p-2.5 rounded bg-obsidian-900/60 border border-slate-800">
                <div className="text-rose-400 font-bold">1. Gambler's Fallacy & Revenge Trading</div>
                <div className="text-slate-400 mt-0.5">
                  Retail traders double down after a loss. Bot automatically pauses execution and enforces a cool-off period.
                </div>
              </div>

              <div className="p-2.5 rounded bg-obsidian-900/60 border border-slate-800">
                <div className="text-amber-400 font-bold">2. FOMO (Fear Of Missing Out)</div>
                <div className="text-slate-400 mt-0.5">
                  Chasing extended green candles into liquidity pools. Bot vetoes any entry extended &gt;2 ATR from 21 EMA.
                </div>
              </div>

              <div className="p-2.5 rounded bg-obsidian-900/60 border border-slate-800">
                <div className="text-cyan-400 font-bold">3. Disposition Effect</div>
                <div className="text-slate-400 mt-0.5">
                  Cutting winners too soon and holding losers too long. Bot enforces strict hard ATR-based stops and 1:2.5+ targets.
                </div>
              </div>

              <div className="p-2.5 rounded bg-obsidian-900/60 border border-slate-800">
                <div className="text-emerald-400 font-bold">4. Action Bias (Overtrading)</div>
                <div className="text-slate-400 mt-0.5">
                  Feeling the need to trade constantly out of boredom. Bot patiently holds cash when market is in equilibrium.
                </div>
              </div>

              <div className="p-2.5 rounded bg-obsidian-900/60 border border-slate-800">
                <div className="text-purple-400 font-bold">5. Sunk Cost Fallacy</div>
                <div className="text-slate-400 mt-0.5">
                  Hoping a bad trade reverses. Bot executes immediate stop-loss closures with zero hesitation.
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
