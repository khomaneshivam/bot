import React, { useState, useEffect } from "react";
import { Wifi, WifiOff, Clock } from "lucide-react";
import { formatTimeAgo } from "../../utils/formatters";

export function DataFreshness({ lastUpdated, isConnected, isStale = false, className = "" }) {
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  const elapsedSec = lastUpdated ? Math.floor((now - new Date(lastUpdated).getTime()) / 1000) : 999;
  const effectivelyStale = isStale || !isConnected || elapsedSec > 15;

  let statusText = "LIVE";
  let badgeColor = "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
  let Icon = Wifi;

  if (!isConnected) {
    statusText = "DISCONNECTED";
    badgeColor = "bg-rose-500/10 text-rose-400 border-rose-500/30";
    Icon = WifiOff;
  } else if (effectivelyStale) {
    statusText = "STALE DATA";
    badgeColor = "bg-amber-500/10 text-amber-400 border-amber-500/30";
    Icon = Clock;
  }

  return (
    <div className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-md border text-xs font-mono select-none ${badgeColor} ${className}`}>
      <Icon className={`w-3.5 h-3.5 ${isConnected && !effectivelyStale ? "animate-pulse" : ""}`} />
      <span className="font-bold">{statusText}</span>
      <span className="text-slate-400 text-[10px] border-l border-slate-700/60 pl-2">
        {lastUpdated ? formatTimeAgo(lastUpdated) : "No timestamp"}
      </span>
    </div>
  );
}
