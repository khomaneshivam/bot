import React, { useState } from "react";
import { useTrading } from "../../context/TradingContext";
import { StatusBadge } from "../../components/common/StatusBadge";
import { formatTimeAgo, formatTimestamp } from "../../utils/formatters";
import { Globe, ShieldAlert, Clock, AlertTriangle, ExternalLink } from "lucide-react";

export function NewsMacroView() {
  const { telemetry } = useTrading();
  const news = telemetry.news || {
    articles: [],
    economic_calendar: [],
    news_shield_active: false,
    feed_online: true,
  };

  const [activeCategory, setActiveCategory] = useState("ALL");

  const articles = news.articles || [];
  const calendar = news.economic_calendar || [];
  const isFeedOnline = news.feed_online !== false && articles.length > 0;

  const filteredArticles = articles.filter((a) => {
    if (activeCategory === "ALL") return true;
    if (activeCategory === "GOLD") return (a.title + a.snippet).toLowerCase().includes("gold");
    if (activeCategory === "FOREX") return (a.title + a.snippet).toLowerCase().includes("dollar") || (a.title + a.snippet).toLowerCase().includes("dxy");
    if (activeCategory === "CENTRAL_BANKS") return (a.title + a.snippet).toLowerCase().includes("fed") || (a.title + a.snippet).toLowerCase().includes("fomc") || (a.title + a.snippet).toLowerCase().includes("rate");
    return true;
  });

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6 select-none bg-slate-950">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-800">
        <div>
          <h1 className="text-base font-bold font-mono text-white tracking-wide flex items-center gap-2">
            <Globe className="w-4 h-4 text-sky-400" />
            <span>MACROECONOMIC RADAR & SCHEDULED BLACKOUT WINDOWS</span>
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            High-impact calendar releases, scheduled blackout volatility shields, and verified RSS feeds.
          </p>
        </div>

        <StatusBadge
          status={isFeedOnline ? "ONLINE" : "UNKNOWN"}
          label={isFeedOnline ? "NEWS STATUS: FRESH" : "NEWS STATUS: UNKNOWN"}
        />
      </div>

      {/* Visual Macro Blackout Windows Section */}
      <div className="p-4 rounded-lg bg-slate-900 border border-slate-800 space-y-3 shadow-lg">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <span className="text-xs font-mono font-bold uppercase text-white tracking-wider flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-amber-400" />
            Scheduled Macro Blackout Windows
          </span>
          <span className="text-[11px] font-mono text-slate-400">
            Automated Entry Freeze Window (-10m → +15m)
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 font-mono text-xs">
          <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 space-y-1.5">
            <div className="flex justify-between items-center">
              <span className="font-bold text-rose-400">USD HIGH IMPACT</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30">
                ACTIVE SHIELD
              </span>
            </div>
            <div className="text-white font-bold text-sm">US Non-Farm Payrolls (NFP)</div>
            <div className="text-slate-400 text-[11px]">13:30 UTC · BLS Release</div>
            <div className="p-1.5 rounded bg-rose-950/40 border border-rose-800/40 text-[11px] text-rose-300 font-bold text-center mt-2">
              TRADING BLOCK: -10m → +15m
            </div>
          </div>

          <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 space-y-1.5">
            <div className="flex justify-between items-center">
              <span className="font-bold text-amber-400">USD HIGH IMPACT</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                SCHEDULED
              </span>
            </div>
            <div className="text-white font-bold text-sm">FOMC Rate Decision & Presser</div>
            <div className="text-slate-400 text-[11px]">18:00 UTC · Federal Reserve</div>
            <div className="p-1.5 rounded bg-slate-900 border border-slate-800 text-[11px] text-amber-300 font-bold text-center mt-2">
              TRADING BLOCK: -15m → +30m
            </div>
          </div>

          <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 space-y-1.5">
            <div className="flex justify-between items-center">
              <span className="font-bold text-amber-400">EUR HIGH IMPACT</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                SCHEDULED
              </span>
            </div>
            <div className="text-white font-bold text-sm">ECB Monetary Policy Statement</div>
            <div className="text-slate-400 text-[11px]">12:15 UTC · ECB Council</div>
            <div className="p-1.5 rounded bg-slate-900 border border-slate-800 text-[11px] text-amber-300 font-bold text-center mt-2">
              TRADING BLOCK: -10m → +15m
            </div>
          </div>
        </div>
      </div>

      {/* Live News Feed Filtering & Stream */}
      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 bg-slate-900 p-1 rounded-lg border border-slate-800 text-xs font-mono">
            {["ALL", "GOLD", "FOREX", "CENTRAL_BANKS"].map((cat) => (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`px-3 py-1 rounded font-medium transition-colors ${
                  activeCategory === cat ? "bg-sky-600 text-white font-bold" : "text-slate-400 hover:text-white"
                }`}
              >
                {cat.replace(/_/g, " ")}
              </button>
            ))}
          </div>

          <div className="text-xs font-mono text-slate-400">
            Showing {filteredArticles.length} verified news catalysts
          </div>
        </div>

        {!isFeedOnline ? (
          <div className="p-8 rounded-lg bg-slate-900 border border-slate-800 text-center font-mono text-xs text-slate-400 space-y-2">
            <AlertTriangle className="w-6 h-6 text-amber-400 mx-auto" />
            <div className="font-bold text-slate-200 uppercase">NEWS STATUS: UNKNOWN</div>
            <div className="max-w-md mx-auto">
              Real-time financial RSS feeds are temporarily unreachable. Synthetic fallback headlines are strictly prohibited in production.
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {filteredArticles.map((article, idx) => (
              <div
                key={idx}
                className="p-4 rounded-lg bg-slate-900 border border-slate-800 space-y-2.5 flex flex-col justify-between"
              >
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-sky-400 border border-slate-700">
                      {article.source || "Reuters / Bloomberg"}
                    </span>
                    <StatusBadge
                      status={article.is_stale ? "WARN" : "HEALTHY"}
                      label={article.is_stale ? "STALE" : "FRESH"}
                      size="sm"
                    />
                  </div>

                  <h3 className="text-xs font-bold font-mono text-white leading-snug">
                    {article.title}
                  </h3>

                  <p className="text-[11px] text-slate-300 leading-relaxed font-sans line-clamp-2">
                    {article.snippet}
                  </p>
                </div>

                <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] font-mono text-slate-400">
                  <span>Published: {article.published_at || "Recent"}</span>
                  <span>Impact: <strong className="text-amber-400 uppercase">{article.impact || "HIGH"}</strong></span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
