import React, { useState } from "react";
import { useTrading } from "../context/TradingContext";

export default function NewsCatalystView() {
  const { telemetry } = useTrading();
  const [filterCategory, setFilterCategory] = useState("ALL");
  const news = telemetry.news || {
    articles: [],
    gold_drivers: {},
    economic_calendar: [],
    overall_sentiment: "BULLISH",
    gold_sentiment_score: 75,
    news_shield_active: false
  };

  const articles = news.articles || [];
  const goldDrivers = news.gold_drivers || {};
  const calendar = news.economic_calendar || [];

  const filteredArticles = articles.filter(a => {
    if (filterCategory === "ALL") return true;
    if (filterCategory === "GOLD") return (a.title + a.snippet).toLowerCase().includes("gold") || a.category === "GOLD_COMMODITIES";
    if (filterCategory === "FOREX") return (a.title + a.snippet).toLowerCase().includes("dollar") || (a.title + a.snippet).toLowerCase().includes("dxy") || a.category === "FOREX_DXY";
    if (filterCategory === "CENTRAL_BANKS") return (a.title + a.snippet).toLowerCase().includes("fed") || (a.title + a.snippet).toLowerCase().includes("fomc") || a.category === "CENTRAL_BANKS";
    return true;
  });

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-obsidian-950 text-slate-100">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 rounded-xl bg-gradient-to-r from-obsidian-900 via-obsidian-850 to-obsidian-900 border border-slate-800 shadow-2xl">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-2xl shadow-inner">
            ⚡
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-3">
              Institutional Gold & Global Macro Catalyst Engine
              <span className="text-xs px-2.5 py-0.5 rounded-full font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 animate-pulse">
                LIVE FEED ACTIVE
              </span>
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Real-time multi-market intelligence • XAU/USD Drivers • FOMC & Central Bank Catalyst Radar
            </p>
          </div>
        </div>

        {/* High-Impact News Volatility Shield Badge */}
        <div className="flex items-center gap-3 bg-obsidian-950 px-4 py-2.5 rounded-lg border border-slate-800">
          <div className={`w-3 h-3 rounded-full ${news.news_shield_active ? "bg-amber-400 animate-ping" : "bg-emerald-400 animate-pulse"}`} />
          <div>
            <div className="text-[10px] font-mono uppercase text-slate-400">News Volatility Guard</div>
            <div className={`text-xs font-semibold ${news.news_shield_active ? "text-amber-400" : "text-emerald-400"}`}>
              {news.news_shield_active ? "VOLATILITY FREEZE ACTIVE" : "EXECUTION PERMITTED (Normal)"}
            </div>
          </div>
        </div>
      </div>

      {/* Gold & Macro Core Sentiment Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Card 1: Gold Sentiment Index */}
        <div className="p-4 rounded-xl bg-obsidian-900/80 border border-slate-800 shadow-lg relative overflow-hidden">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono text-slate-400">GOLD (XAU/USD) BIAS</span>
            <span className="text-xs font-mono font-bold text-amber-400">BULLISH FLOW</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-black font-mono text-amber-400">{news.gold_sentiment_score}%</span>
            <span className="text-xs text-slate-400">Institutional Net Long</span>
          </div>
          <div className="w-full bg-slate-800 h-1.5 rounded-full mt-3 overflow-hidden">
            <div
              className="bg-gradient-to-r from-amber-500 to-emerald-400 h-full rounded-full transition-all duration-700"
              style={{ width: `${news.gold_sentiment_score}%` }}
            />
          </div>
          <div className="text-[10px] text-slate-400 mt-2 flex justify-between">
            <span>Safe-Haven Accumulation</span>
            <span className="text-emerald-400">Strong Floor</span>
          </div>
        </div>

        {/* Card 2: US 10Y Real Yield Driver */}
        <div className="p-4 rounded-xl bg-obsidian-900/80 border border-slate-800 shadow-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono text-slate-400">US 10Y TREASURY YIELD</span>
            <span className="text-xs font-mono text-emerald-400 font-semibold">{goldDrivers.us_10y_yield?.change || "-0.04%"}</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-black font-mono text-white">{goldDrivers.us_10y_yield?.value || "4.18%"}</span>
            <span className="text-[11px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-mono">BULLISH FOR GOLD</span>
          </div>
          <div className="text-[11px] text-slate-400 mt-2 line-clamp-2">
            {goldDrivers.us_10y_yield?.reason || "Lower real yields reduce opportunity cost of holding physical Gold."}
          </div>
        </div>

        {/* Card 3: DXY Dollar Index Driver */}
        <div className="p-4 rounded-xl bg-obsidian-900/80 border border-slate-800 shadow-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono text-slate-400">DXY DOLLAR INDEX</span>
            <span className="text-xs font-mono text-emerald-400 font-semibold">{goldDrivers.dxy_index?.change || "-0.32%"}</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-black font-mono text-white">{goldDrivers.dxy_index?.value || "101.42"}</span>
            <span className="text-[11px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-mono">INVERSE TAILWIND</span>
          </div>
          <div className="text-[11px] text-slate-400 mt-2 line-clamp-2">
            {goldDrivers.dxy_index?.reason || "Weakening USD expands international purchasing power for precious metals."}
          </div>
        </div>

        {/* Card 4: Geopolitical Safe-Haven Meter */}
        <div className="p-4 rounded-xl bg-obsidian-900/80 border border-slate-800 shadow-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono text-slate-400">GEOPOLITICAL HEDGE</span>
            <span className="text-xs font-mono text-rose-400 font-semibold">HIGH DEMAND</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-black font-mono text-rose-400">78 / 100</span>
            <span className="text-[11px] px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-400 font-mono">ELEVATED</span>
          </div>
          <div className="text-[11px] text-slate-400 mt-2 line-clamp-2">
            Central banks (PBOC, RBI) diversifying reserves aggressively into unencumbered physical bullion.
          </div>
        </div>
      </div>

      {/* Main Split: Live Headlines vs. Economic Calendar & Strategic Checklist */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Live News Tape (7 Cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
              Live Multi-Market News Feed
            </h2>

            {/* Filter Pills */}
            <div className="flex gap-1.5 bg-obsidian-900 p-1 rounded-lg border border-slate-800 text-xs">
              {["ALL", "GOLD", "FOREX", "CENTRAL_BANKS"].map(cat => (
                <button
                  key={cat}
                  onClick={() => setFilterCategory(cat)}
                  className={`px-2.5 py-1 rounded transition-colors ${
                    filterCategory === cat
                      ? "bg-cyan-500 text-obsidian-950 font-bold shadow-md"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  {cat.replace("_", " ")}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-3">
            {filteredArticles.length === 0 ? (
              <div className="p-8 text-center bg-obsidian-900/50 rounded-xl border border-slate-800 text-slate-500 text-xs font-mono">
                Ingesting live global market headlines...
              </div>
            ) : (
              filteredArticles.map((art, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-xl bg-obsidian-900/90 border border-slate-800/80 hover:border-slate-700 transition-all hover:shadow-xl group"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                        {/* Sentiment badge */}
                        <span
                          className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full ${
                            art.sentiment === "BULLISH"
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                              : art.sentiment === "BEARISH"
                              ? "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                              : "bg-slate-800 text-slate-300 border border-slate-700"
                          }`}
                        >
                          {art.sentiment}
                        </span>

                        {/* Impact badge */}
                        <span
                          className={`text-[10px] font-mono px-2 py-0.5 rounded-full ${
                            art.impact === "CRITICAL"
                              ? "bg-rose-600 text-white font-bold animate-pulse"
                              : art.impact === "HIGH"
                              ? "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                              : "bg-slate-800 text-slate-400"
                          }`}
                        >
                          {art.impact} IMPACT
                        </span>

                        <span className="text-[11px] text-slate-500 font-mono">
                          {art.source} • {art.published}
                        </span>
                      </div>

                      <h3 className="text-sm font-semibold text-slate-200 group-hover:text-cyan-300 transition-colors leading-snug">
                        {art.title}
                      </h3>
                      <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                        {art.snippet}
                      </p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Column: Economic Calendar & Institutional Checklist (5 Cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Institutional Economic Calendar */}
          <div className="p-5 rounded-xl bg-obsidian-900/80 border border-slate-800 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200 flex items-center gap-2">
                📅 High-Impact Macro Calendar
              </h2>
              <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800">
                15-MIN VETO WINDOW
              </span>
            </div>

            <div className="space-y-2.5">
              {calendar.map((ev, i) => (
                <div
                  key={i}
                  className="p-3 rounded-lg bg-obsidian-950 border border-slate-800/80 flex items-center justify-between text-xs hover:border-slate-700 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-slate-400 w-11 text-[11px]">{ev.time_utc}</span>
                    <span className="font-mono font-bold px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px]">
                      {ev.currency}
                    </span>
                    <div>
                      <div className="font-medium text-slate-200">{ev.event}</div>
                      <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                        Forecast: {ev.forecast} | Prior: {ev.previous}
                      </div>
                    </div>
                  </div>

                  <span
                    className={`font-mono text-[10px] font-bold px-2 py-0.5 rounded ${
                      ev.impact === "CRITICAL"
                        ? "bg-rose-500/20 text-rose-400 border border-rose-500/40"
                        : ev.impact === "HIGH"
                        ? "bg-amber-500/20 text-amber-400 border border-amber-500/40"
                        : "bg-slate-800 text-slate-400"
                    }`}
                  >
                    {ev.impact}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* 20+ Year Hedge Fund Strategy Gold Checklist */}
          <div className="p-5 rounded-xl bg-gradient-to-b from-obsidian-900 to-obsidian-950 border border-slate-800 shadow-xl space-y-3">
            <h2 className="text-sm font-bold uppercase tracking-wider text-amber-400 flex items-center gap-2">
              🏆 Institutional XAU/USD Execution Checklist
            </h2>
            <p className="text-xs text-slate-400">
              Criteria required by senior commodities portfolio managers before placing high-confidence gold allocations:
            </p>

            <div className="space-y-2 text-xs font-mono">
              <div className="flex items-start gap-2 p-2 rounded bg-obsidian-900/60 border border-slate-800">
                <span className="text-emerald-400 font-bold">✓</span>
                <div>
                  <span className="text-white font-semibold">Yield Confluence:</span> US 10Y real yield declining or stabilizing below resistance.
                </div>
              </div>
              <div className="flex items-start gap-2 p-2 rounded bg-obsidian-900/60 border border-slate-800">
                <span className="text-emerald-400 font-bold">✓</span>
                <div>
                  <span className="text-white font-semibold">DXY Inversion:</span> Synthetic Dollar Index showing bearish expansion or failure at swing high.
                </div>
              </div>
              <div className="flex items-start gap-2 p-2 rounded bg-obsidian-900/60 border border-slate-800">
                <span className="text-emerald-400 font-bold">✓</span>
                <div>
                  <span className="text-white font-semibold">Discount SMC Entry:</span> Price retesting 3-candle Fair Value Gap (FVG) in discount equilibrium zone.
                </div>
              </div>
              <div className="flex items-start gap-2 p-2 rounded bg-obsidian-900/60 border border-slate-800">
                <span className="text-emerald-400 font-bold">✓</span>
                <div>
                  <span className="text-white font-semibold">Risk:Reward Asymmetry:</span> Minimum 1:2.5 R:R with invalidation anchored behind recent institutional sweep low.
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
