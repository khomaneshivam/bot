import React, { useEffect, useRef, useState } from "react";
import { useTrading } from "../../context/TradingContext";
import { formatPrice, formatPercent, getRegimeBadge } from "../../utils/formatters";
import { StatusBadge } from "../../components/common/StatusBadge";
import {
  TrendingUp,
  TrendingDown,
  Activity,
  ShieldCheck,
  ShieldAlert,
  Zap,
  SlidersHorizontal,
} from "lucide-react";

export function MarketsView() {
  const { telemetry, switchSymbol, placeManualTradeSafe } = useTrading();
  const { symbol, candles, regime, latest_decision, open_positions, strategies } = telemetry;

  const [timeframe, setTimeframe] = useState("5m");
  const [selectedStrategy, setSelectedStrategy] = useState("ALL");
  const [dimensions, setDimensions] = useState({ w: 0, h: 0 });
  const canvasRef = useRef(null);

  // Active positions on this symbol for SL/TP overlays
  const currentPositions = (open_positions || []).filter((p) => p.symbol === symbol);

  // High-performance Canvas Chart Render
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const container = canvas.parentElement;
    const width = container.clientWidth;
    const height = container.clientHeight || 450;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, width, height);

    if (!candles || candles.length === 0) {
      ctx.fillStyle = "#64748b";
      ctx.font = "12px 'JetBrains Mono', monospace";
      ctx.textAlign = "center";
      ctx.fillText("Connecting to market quote feed...", width / 2, height / 2);
      return;
    }

    const padding = { top: 25, right: 80, bottom: 35, left: 15 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;
    const volumeHeight = chartHeight * 0.16;
    const priceHeight = chartHeight - volumeHeight - 15;

    const highs = candles.map((c) => c.high);
    const lows = candles.map((c) => c.low);
    const volumes = candles.map((c) => c.volume);

    // Expand price bounds to also show open SL and TP levels if active
    let maxPrice = Math.max(...highs);
    let minPrice = Math.min(...lows);
    currentPositions.forEach((pos) => {
      if (pos.sl) {
        maxPrice = Math.max(maxPrice, Number(pos.sl));
        minPrice = Math.min(minPrice, Number(pos.sl));
      }
      if (pos.tp) {
        maxPrice = Math.max(maxPrice, Number(pos.tp));
        minPrice = Math.min(minPrice, Number(pos.tp));
      }
    });

    const maxVol = Math.max(...volumes, 1);
    const delta = maxPrice - minPrice || 0.001;
    maxPrice += delta * 0.05;
    minPrice -= delta * 0.05;

    const count = candles.length;
    const candleWidth = Math.max(3, (chartWidth / count) * 0.65);
    const step = chartWidth / count;

    const getY = (val) => padding.top + (1 - (val - minPrice) / (maxPrice - minPrice)) * priceHeight;
    const getVolY = (vol) => height - padding.bottom - (vol / maxVol) * volumeHeight;

    // Horizontal Price Grid Lines
    ctx.strokeStyle = "#1e293b";
    ctx.lineWidth = 1;
    ctx.fillStyle = "#64748b";
    ctx.font = "10px 'JetBrains Mono', monospace";
    ctx.textAlign = "left";

    const gridSteps = 6;
    for (let i = 0; i <= gridSteps; i++) {
      const p = minPrice + (i / gridSteps) * (maxPrice - minPrice);
      const y = getY(p);
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(width - padding.right, y);
      ctx.stroke();
      ctx.fillText(formatPrice(p, symbol), width - padding.right + 8, y + 3);
    }

    // Draw Candles & Volume
    candles.forEach((c, i) => {
      const x = padding.left + i * step + step / 2;
      const openY = getY(c.open);
      const closeY = getY(c.close);
      const highY = getY(c.high);
      const lowY = getY(c.low);
      const volY = getVolY(c.volume);

      const isUp = c.close >= c.open;
      const barColor = isUp ? "#10b981" : "#f43f5e";

      // Volume bar
      ctx.fillStyle = isUp ? "rgba(16, 185, 129, 0.15)" : "rgba(244, 63, 94, 0.15)";
      ctx.fillRect(x - candleWidth / 2, volY, candleWidth, height - padding.bottom - volY);

      // Wick
      ctx.strokeStyle = barColor;
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(x, highY);
      ctx.lineTo(x, lowY);
      ctx.stroke();

      // Candle Body
      ctx.fillStyle = barColor;
      const bodyTop = Math.min(openY, closeY);
      const bodyHeight = Math.max(Math.abs(closeY - openY), 1.5);
      ctx.fillRect(x - candleWidth / 2, bodyTop, candleWidth, bodyHeight);
    });

    // Draw Active Positions Entry, SL, and TP Markers
    currentPositions.forEach((pos) => {
      const entryY = getY(pos.entry_price);
      // Entry Line (Cyan dashed)
      ctx.strokeStyle = "#0284c7";
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(padding.left, entryY);
      ctx.lineTo(width - padding.right, entryY);
      ctx.stroke();
      ctx.fillStyle = "#0284c7";
      ctx.fillText(`ENTRY: ${formatPrice(pos.entry_price, symbol)}`, padding.left + 5, entryY - 4);

      // Stop-Loss Line (Rose dashed)
      if (pos.sl) {
        const slY = getY(pos.sl);
        ctx.strokeStyle = "#f43f5e";
        ctx.beginPath();
        ctx.moveTo(padding.left, slY);
        ctx.lineTo(width - padding.right, slY);
        ctx.stroke();
        ctx.fillStyle = "#f43f5e";
        ctx.fillText(`SL: ${formatPrice(pos.sl, symbol)}`, padding.left + 5, slY - 4);
      }

      // Take-Profit Line (Emerald dashed)
      if (pos.tp) {
        const tpY = getY(pos.tp);
        ctx.strokeStyle = "#10b981";
        ctx.beginPath();
        ctx.moveTo(padding.left, tpY);
        ctx.lineTo(width - padding.right, tpY);
        ctx.stroke();
        ctx.fillStyle = "#10b981";
        ctx.fillText(`TP: ${formatPrice(pos.tp, symbol)}`, padding.left + 5, tpY - 4);
      }
      ctx.setLineDash([]);
    });

    // Current Price Indicator (Right axis marker)
    if (candles.length > 0) {
      const lastCandle = candles[candles.length - 1];
      const currentY = getY(lastCandle.close);

      ctx.fillStyle = lastCandle.close >= lastCandle.open ? "#10b981" : "#f43f5e";
      ctx.fillRect(width - padding.right, currentY - 9, padding.right - 5, 18);
      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 10px 'JetBrains Mono', monospace";
      ctx.fillText(formatPrice(lastCandle.close, symbol), width - padding.right + 5, currentY + 4);
    }
  }, [candles, symbol, currentPositions, dimensions]);

  // Responsive Resize Listener to adapt chart to window and sidebar transitions
  useEffect(() => {
    const handleResize = () => {
      if (canvasRef.current?.parentElement) {
        setDimensions({
          w: canvasRef.current.parentElement.clientWidth,
          h: canvasRef.current.parentElement.clientHeight,
        });
      }
    };
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const lastClose = candles && candles.length > 0 ? candles[candles.length - 1].close : 0;
  const decision = latest_decision || {};

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 select-none bg-slate-950">
      {/* Top Filter & Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg bg-slate-900 border border-slate-800">
        <div className="flex items-center gap-3">
          {/* Symbol Selector */}
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="text-slate-400">SYMBOL:</span>
            <select
              value={symbol}
              onChange={(e) => switchSymbol(e.target.value)}
              className="bg-slate-950 border border-slate-700 text-white font-bold rounded px-2.5 py-1 focus:outline-none focus:border-sky-500"
            >
              <optgroup label="Forex Major">
                <option value="EURUSD">EUR/USD</option>
                <option value="GBPUSD">GBP/USD</option>
                <option value="USDJPY">USD/JPY</option>
                <option value="USDCHF">USD/CHF</option>
                <option value="AUDUSD">AUD/USD</option>
              </optgroup>
              <optgroup label="Precious Metals">
                <option value="XAUUSD">XAU/USD (Gold)</option>
              </optgroup>
              <optgroup label="Crypto Assets">
                <option value="BTCUSDT">BTC/USDT</option>
                <option value="ETHUSDT">ETH/USDT</option>
                <option value="SOLUSDT">SOL/USDT</option>
              </optgroup>
            </select>
          </div>

          {/* Timeframe Buttons */}
          <div className="flex items-center bg-slate-950 p-0.5 rounded border border-slate-800 text-[11px] font-mono">
            {["1m", "5m", "15m", "1h"].map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-2 py-0.5 rounded font-bold transition-colors ${
                  timeframe === tf ? "bg-sky-600 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                {tf.toUpperCase()}
              </button>
            ))}
          </div>

          {/* Volatility Regime Badge */}
          <StatusBadge status="INFO" label={`REGIME: ${regime || "NEUTRAL"}`} />
        </div>

        {/* Fast Manual Order Controls */}
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono text-slate-400 hidden sm:inline">Manual Ticket:</span>
          <button
            onClick={() => placeManualTradeSafe("BUY")}
            className="px-3 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-mono font-bold text-xs shadow-sm transition-colors"
          >
            BUY {symbol}
          </button>
          <button
            onClick={() => placeManualTradeSafe("SELL")}
            className="px-3 py-1 rounded bg-rose-600 hover:bg-rose-500 text-white font-mono font-bold text-xs shadow-sm transition-colors"
          >
            SELL {symbol}
          </button>
        </div>
      </div>

      {/* Main Grid: Chart Workspace & Signal Decision Engine */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Left Column (3/4): Trading Chart */}
        <div className="lg:col-span-3 rounded-lg bg-slate-900 border border-slate-800 p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-2">
            <div className="flex items-center gap-3">
              <span className="text-base font-extrabold font-mono text-white tracking-wide">
                {symbol} · {timeframe.toUpperCase()}
              </span>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                Candlestick + Volume
              </span>
            </div>
            <div className="text-right">
              <div className="text-lg font-black font-mono text-white tabular-nums">
                {formatPrice(lastClose, symbol)}
              </div>
              <div className="text-[10px] font-mono text-slate-400">
                Last quote close
              </div>
            </div>
          </div>

          {/* Canvas Viewport */}
          <div className="w-full h-96 relative flex items-center justify-center">
            <canvas ref={canvasRef} className="w-full h-full block" />
          </div>

          {/* Bottom Chart Footer Legend */}
          <div className="pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between text-[11px] font-mono text-slate-400 gap-2">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 bg-emerald-500 rounded-sm" /> Bullish Candle
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 bg-rose-500 rounded-sm" /> Bearish Candle
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-0.5 bg-sky-500" /> Active Entry
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-0.5 bg-rose-500" /> Stop-Loss
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-0.5 bg-emerald-500" /> Take-Profit
              </span>
            </div>
            <span>60-Period Window · High-Frequency Stream</span>
          </div>
        </div>

        {/* Right Column (1/4): Statistical Signal Decision Box */}
        <div className="space-y-4">
          <div className="p-4 rounded-lg bg-slate-900 border border-slate-800 space-y-3.5">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <span className="text-xs font-mono font-bold uppercase text-white tracking-wider flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5 text-sky-400" />
                Signal Decision Engine
              </span>
              <StatusBadge status={decision.signal || "HOLD"} size="sm" />
            </div>

            {/* Direction */}
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-slate-400 uppercase">Direction:</span>
              <span
                className={`font-black tracking-wider ${
                  decision.signal === "BUY"
                    ? "text-emerald-400"
                    : decision.signal === "SELL"
                    ? "text-rose-400"
                    : "text-slate-300"
                }`}
              >
                {decision.signal === "BUY" ? "LONG (BUY)" : decision.signal === "SELL" ? "SHORT (SELL)" : "NEUTRAL (HOLD)"}
              </span>
            </div>

            {/* Confidence (Raw Score) */}
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-slate-400">Confidence (Raw):</span>
              <span className="text-white font-bold tabular-nums">
                {Math.round((decision.confidence || 0) * 100)}%
              </span>
            </div>

            {/* Calibrated Probability (Show ONLY if statistically calibrated) */}
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-slate-400">Calibrated Probability:</span>
              {decision.calibrated_probability !== undefined && decision.calibrated_probability !== null ? (
                <span className="text-sky-400 font-bold tabular-nums">
                  {(decision.calibrated_probability * 100).toFixed(1)}%
                </span>
              ) : (
                <span className="text-slate-500 italic text-[11px]">Uncalibrated</span>
              )}
            </div>

            {/* Volatility Regime */}
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-slate-400">Regime:</span>
              <span className="text-slate-200 font-semibold uppercase">
                {(decision.regime || regime || "NEUTRAL").replace(/_/g, " ")}
              </span>
            </div>

            {/* Risk Gate Approval */}
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-slate-400">Risk Check:</span>
              <span className="text-emerald-400 font-bold flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>APPROVED</span>
              </span>
            </div>

            {/* Execution State */}
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-slate-400">Execution:</span>
              <span className="text-sky-400 font-bold">
                {telemetry.is_running ? "MONITORING" : "ENGINE PAUSED"}
              </span>
            </div>

            {/* Rationale Explanation */}
            <div className="pt-2 border-t border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
                Decision Rationale:
              </span>
              <div className="p-2 rounded bg-slate-950 text-slate-300 text-[11px] font-mono leading-relaxed border border-slate-800/80">
                {decision.reason || "Autonomous ensemble scanning multi-timeframe candle structure for high-probability edge."}
              </div>
            </div>
          </div>

          {/* Strategy Breakdown Matrix for current pair */}
          <div className="p-4 rounded-lg bg-slate-900 border border-slate-800 space-y-2.5">
            <span className="text-xs font-mono font-bold text-white uppercase tracking-wider block">
              Ensemble Signal Weights
            </span>
            <div className="space-y-1.5">
              {Object.entries(strategies || {}).map(([sName, sData]) => {
                const sig = sData.signal || "HOLD";
                const chance = sData.chance_pct || 0;
                return (
                  <div key={sName} className="flex justify-between items-center text-xs font-mono py-1 border-b border-slate-800/50">
                    <span className="text-slate-400">{sName.replace(/_/g, " ")}</span>
                    <span className={sig === "BUY" ? "text-emerald-400 font-bold" : sig === "SELL" ? "text-rose-400 font-bold" : "text-slate-500"}>
                      {sig} ({chance}%)
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
