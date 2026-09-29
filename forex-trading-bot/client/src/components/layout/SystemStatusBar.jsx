import React, { useState, useEffect } from "react";
import { useTrading } from "../../context/TradingContext";
import { formatTimestamp } from "../../utils/formatters";
import { Wifi, Activity, Shield, CheckCircle, Database } from "lucide-react";

export function SystemStatusBar() {
  const { isConnected, latencyMs, telemetry } = useTrading();
  const [utcTime, setUtcTime] = useState("");

  useEffect(() => {
    const updateClock = () => {
      const now = new Date();
      setUtcTime(now.toUTCString().replace("GMT", "UTC"));
    };
    updateClock();
    const interval = setInterval(updateClock, 1000);
    return () => clearInterval(interval);
  }, []);

  const { broker_connected, feed_fresh, circuit_breakers, regime } = telemetry;
  const isHealthy = broker_connected && feed_fresh && !circuit_breakers?.tripped;

  return (
    <footer className="h-7 px-4 bg-slate-950 border-t border-slate-800/80 flex items-center justify-between text-[11px] font-mono text-slate-400 select-none shrink-0 z-20">
      {/* Left: Stream Telemetry & Broker Link */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <Wifi className={`w-3 h-3 ${isConnected ? "text-emerald-400" : "text-rose-400"}`} />
          <span>WS: <strong className={isConnected ? "text-emerald-400" : "text-rose-400"}>{isConnected ? "ESTABLISHED" : "DISCONNECTED"}</strong></span>
        </div>

        {latencyMs !== null && (
          <div className="flex items-center gap-1">
            <span>PING: <strong className="text-slate-200">{latencyMs}ms</strong></span>
          </div>
        )}

        <div className="flex items-center gap-1.5 border-l border-slate-800 pl-3">
          <Database className={`w-3 h-3 ${broker_connected ? "text-emerald-400" : "text-rose-400"}`} />
          <span>BROKER: <strong className={broker_connected ? "text-emerald-400" : "text-rose-400"}>{broker_connected ? "CONNECTED" : "OFFLINE"}</strong></span>
        </div>

        <div className="hidden sm:flex items-center gap-1.5 border-l border-slate-800 pl-3">
          <span>MARKET REGIME: <strong className="text-sky-400 uppercase">{(regime || "NEUTRAL").replace(/_/g, " ")}</strong></span>
        </div>
      </div>

      {/* Right: Risk Engine State & UTC Clock */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <Shield className={`w-3 h-3 ${!circuit_breakers?.tripped ? "text-emerald-400" : "text-rose-400"}`} />
          <span>RISK ENGINE: <strong className={!circuit_breakers?.tripped ? "text-emerald-400" : "text-rose-400"}>{!circuit_breakers?.tripped ? "ARMED" : "HALTED"}</strong></span>
        </div>

        <div className="hidden md:flex items-center gap-1.5 border-l border-slate-800 pl-3 text-slate-300">
          <Activity className="w-3 h-3 text-sky-400" />
          <span>SYSTEM: <strong className={isHealthy ? "text-emerald-400" : "text-amber-400"}>{isHealthy ? "HEALTHY" : "DEGRADED"}</strong></span>
        </div>

        <div className="border-l border-slate-800 pl-3 text-slate-400">
          <span>{utcTime}</span>
        </div>
      </div>
    </footer>
  );
}
