/**
 * QuantAI Terminal - Live Terminal Workspace Component
 */

import React, { useEffect, useRef } from "react";
import { useTrading } from "../context/TradingContext";
import { formatCurrency, formatPnL, formatPrice, getPnLColorClass, getRegimeBadge } from "../utils/formatters";

export function TerminalView() {
  const { telemetry, placeManualTrade, closePosition } = useTrading();
  const {
    symbol,
    candles,
    open_positions,
    account,
    regime,
    ml_stats,
    latest_decision,
    strategies,
    terminal_logs,
  } = telemetry;

  const canvasRef = useRef(null);

  // Render chart on canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const width = canvas.parentElement.clientWidth;
    const height = canvas.parentElement.clientHeight || 420;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, width, height);

    if (!candles || candles.length === 0) {
      ctx.fillStyle = "rgba(148, 163, 184, 0.6)";
      ctx.font = "14px 'Inter', sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Connecting to market feed...", width / 2, height / 2);
      return;
    }

    const padding = { top: 20, right: 70, bottom: 35, left: 15 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;
    const volumeHeight = chartHeight * 0.18;
    const priceHeight = chartHeight - volumeHeight - 15;

    const highs = candles.map((c) => c.high);
    const lows = candles.map((c) => c.low);
    const volumes = candles.map((c) => c.volume);

    let maxPrice = Math.max(...highs);
    let minPrice = Math.min(...lows);
    const maxVol = Math.max(...volumes, 1);
    const delta = maxPrice - minPrice || 1;
    maxPrice += delta * 0.05;
    minPrice -= delta * 0.05;

    const count = candles.length;
    const candleWidth = Math.max(3, (chartWidth / count) * 0.65);
    const step = chartWidth / count;

    const getY = (val) => padding.top + (1 - (val - minPrice) / (maxPrice - minPrice)) * priceHeight;
    const getVolY = (vol) => height - padding.bottom - (vol / maxVol) * volumeHeight;

    // Grid lines
    ctx.strokeStyle = "rgba(255, 255, 255, 0.05)";
    ctx.lineWidth = 1;
    ctx.fillStyle = "rgba(148, 163, 184, 0.7)";
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
      ctx.fillText(p.toFixed(4), width - padding.right + 8, y + 3);
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
      const barColor = isUp ? "#00f59b" : "#ff3366";

      // Volume bar
      ctx.fillStyle = isUp ? "rgba(0, 245, 155, 0.2)" : "rgba(255, 51, 102, 0.2)";
      ctx.fillRect(x - candleWidth / 2, volY, candleWidth, height - padding.bottom - volY);

      // Wick
      ctx.strokeStyle = barColor;
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(x, highY);
      ctx.lineTo(x, lowY);
      ctx.stroke();

      // Body
      ctx.fillStyle = barColor;
      const bodyTop = Math.min(openY, closeY);
      const bodyHeight = Math.max(Math.abs(closeY - openY), 1.5);
      ctx.fillRect(x - candleWidth / 2, bodyTop, candleWidth, bodyHeight);
    });
  }, [candles]);

  const regimeBadge = getRegimeBadge(regime);
  const lastClose = candles && candles.length > 0 ? candles[candles.length - 1].close : 0;

  return (
    <main className="dashboard-container">
      {/* Top Metrics Row */}
      <section className="metrics-row" aria-label="Key Performance Indicators">
        {/* Card 1: Total Equity */}
        <div className="metric-card glass-panel">
          <div className="metric-header">
            <span className="metric-title">TOTAL EQUITY</span>
            <span className="metric-badge badge-emerald">{(account.mode || "PAPER").toUpperCase()}</span>
          </div>
          <div className="metric-value-wrap">
            <span className="metric-value">{formatCurrency(account.equity)}</span>
            <span
              className={`pnl-badge ${account.unrealized_pnl >= 0 ? "" : "text-red"}`}
              style={{
                background:
                  account.unrealized_pnl >= 0 ? "rgba(16, 185, 129, 0.12)" : "rgba(239, 68, 68, 0.12)",
              }}
            >
              {formatPnL(account.unrealized_pnl)}
            </span>
          </div>
          <div className="metric-subtext">
            Balance: <span className="mono">{formatCurrency(account.balance)}</span> | Realized:{" "}
            <span className={`mono ${getPnLColorClass(account.realized_pnl)}`}>
              {formatPnL(account.realized_pnl)}
            </span>
          </div>
        </div>

        {/* Card 2: Win Rate & Profit Factor */}
        <div className="metric-card glass-panel">
          <div className="metric-header">
            <span className="metric-title">WIN RATE &amp; PROFIT FACTOR</span>
            <span className="metric-badge badge-cyan">{account.total_trades} TRADES</span>
          </div>
          <div className="metric-value-wrap">
            <span className="metric-value">{account.win_rate}%</span>
            <span className="metric-ratio">PF {account.profit_factor}</span>
          </div>
          <div className="progress-bar-wrap">
            <div
              className="progress-bar-fill"
              style={{ width: `${Math.min(account.win_rate || 0, 100)}%` }}
            ></div>
          </div>
          <div className="metric-subtext">
            Wins: <span className="mono text-green">{account.winning_trades}</span> | Losses:{" "}
            <span className="mono text-red">{account.losing_trades}</span>
          </div>
        </div>

        {/* Card 3: Regime */}
        <div className="metric-card glass-panel">
          <div className="metric-header">
            <span className="metric-title">MARKET REGIME</span>
            <span className="metric-badge badge-purple">VOLATILITY RADAR</span>
          </div>
          <div className="metric-value-wrap">
            <span className="metric-value text-cyan" style={{ fontSize: "1.3rem" }}>
              {regimeBadge.label}
            </span>
          </div>
          <div className="metric-subtext">Multi-timeframe variance analyzer active</div>
        </div>

        {/* Card 4: AI Brain */}
        <div className="metric-card glass-panel">
          <div className="metric-header">
            <span className="metric-title">AI BRAIN &amp; SHIELD</span>
            <span className="metric-badge badge-emerald">ADAPTING</span>
          </div>
          <div className="metric-value-wrap">
            <span className="metric-value mono">
              {(ml_stats ? ml_stats.parameters_count || 45000 : 45000).toLocaleString()}
            </span>
            <span className="metric-ratio">PARAMS</span>
          </div>
          <div className="metric-subtext">
            Wrong memorized: <span className="mono text-yellow">{ml_stats ? ml_stats.wrong_trades_memorized || 0 : 0}</span> | Vetoes:{" "}
            <span className="mono text-cyan">{ml_stats ? ml_stats.vetoed_trades_count || 0 : 0}</span>
          </div>
        </div>
      </section>

      {/* Main Trading Area */}
      <section className="main-trading-grid">
        {/* Left Column: Live Chart & Decision Banner */}
        <div className="glass-panel chart-panel">
          <div className="chart-header">
            <div className="chart-title-wrap">
              <span className="chart-symbol">{symbol}</span>
              <span className="chart-timeframe">5M</span>
              <span className="metric-badge badge-purple">LIVE FEED</span>
            </div>
            <div className="chart-price-display">
              <span className="live-price mono">{formatPrice(lastClose, symbol)}</span>
            </div>
          </div>

          <div className="chart-canvas-container" style={{ position: "relative", minHeight: 400 }}>
            <canvas ref={canvasRef} style={{ width: "100%", height: "100%" }}></canvas>
          </div>

          {/* Autonomous Decision Banner */}
          <div className="decision-banner">
            <div className="decision-main">
              <span
                className={`decision-indicator ${
                  latest_decision.signal === "BUY"
                    ? "signal-buy"
                    : latest_decision.signal === "SELL"
                    ? "signal-sell"
                    : "signal-hold"
                }`}
              ></span>
              <span
                className={`font-bold ${
                  latest_decision.signal === "BUY"
                    ? "text-green"
                    : latest_decision.signal === "SELL"
                    ? "text-red"
                    : "text-muted"
                }`}
              >
                {latest_decision.signal || "HOLD"}
              </span>
              <span className="metric-badge badge-cyan">
                CONF {Math.round((latest_decision.confidence || 0) * 100)}%
              </span>
            </div>
            <div className="decision-details">
              <span>{latest_decision.reason || "Evaluating market conditions..."}</span>
            </div>
          </div>
        </div>

        {/* Right Column: Execution & Strategies */}
        <div className="sidebar-workspace">
          {/* Manual Trade Box */}
          <div className="glass-panel execution-panel">
            <div className="panel-header">
              <h2 className="panel-title">⚡ FAST EXECUTION</h2>
              <span className="badge-tag">INSTANT</span>
            </div>
            <div className="execution-buttons">
              <button className="btn-trade btn-buy" onClick={() => placeManualTrade("BUY")}>
                BUY {symbol}
              </button>
              <button className="btn-trade btn-sell" onClick={() => placeManualTrade("SELL")}>
                SELL {symbol}
              </button>
            </div>
          </div>

          {/* Strategy Ensemble Radar */}
          <div className="glass-panel execution-panel">
            <div className="panel-header">
              <h2 className="panel-title">🎯 STRATEGY ENSEMBLE</h2>
              <span className="badge-tag">WEIGHTED</span>
            </div>
            <div className="strategy-list">
              {Object.entries(strategies || {}).map(([name, data]) => (
                <div className="strategy-item" key={name}>
                  <div className="strategy-header">
                    <span>{name.replace(/_/g, " ")}</span>
                    <span className={data.signal === "BUY" ? "text-green" : data.signal === "SELL" ? "text-red" : "text-muted"}>
                      {data.signal || "HOLD"} ({data.chance_pct || 0}%)
                    </span>
                  </div>
                  <div className="strategy-bar-bg">
                    <div
                      className={`strategy-bar-fill ${data.signal === "BUY" ? "bar-buy" : data.signal === "SELL" ? "bar-sell" : "bar-neutral"}`}
                      style={{ width: `${Math.min(data.chance_pct || 0, 100)}%` }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Bottom Workspace: Active Positions & Logs */}
      <section className="bottom-workspace-grid">
        {/* Open Positions */}
        <div className="glass-panel data-card">
          <div className="card-header">
            <h2 className="card-title">📊 ACTIVE POSITIONS</h2>
            <span className="card-tag badge-green">{open_positions.length} OPEN</span>
          </div>
          <div className="table-responsive">
            <table className="quant-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Symbol</th>
                  <th>Type</th>
                  <th>Size</th>
                  <th>Entry Price</th>
                  <th>Current Price</th>
                  <th>SL / TP</th>
                  <th>Floating PnL</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {open_positions.length === 0 ? (
                  <tr>
                    <td colSpan="9" className="text-center text-muted">
                      No open positions. Autonomous engine is scanning for high-probability setups.
                    </td>
                  </tr>
                ) : (
                  open_positions.map((pos) => {
                    const pnl = pos.unrealized_pnl || 0;
                    return (
                      <tr key={pos.id}>
                        <td>#{pos.id}</td>
                        <td>
                          <strong>{pos.symbol}</strong>
                        </td>
                        <td>
                          <span className={pos.direction === "BUY" ? "tag-buy" : "tag-sell"}>
                            {pos.direction}
                          </span>
                        </td>
                        <td>{pos.size}</td>
                        <td>${Number(pos.entry_price).toFixed(4)}</td>
                        <td>${Number(pos.current_price).toFixed(4)}</td>
                        <td>
                          SL: ${pos.sl} / TP: ${pos.tp}
                        </td>
                        <td className={getPnLColorClass(pnl)}>
                          <strong>{formatPnL(pnl)}</strong>
                        </td>
                        <td>
                          <button className="btn-close-pos" onClick={() => closePosition(pos.id)}>
                            Close
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Real-time Telemetry Logs */}
        <div className="glass-panel data-card">
          <div className="card-header">
            <h2 className="card-title">💻 REAL-TIME RISK &amp; ENGINE TERMINAL</h2>
            <span className="card-tag badge-cyan">TELEMETRY</span>
          </div>
          <div className="terminal-log-feed">
            {terminal_logs.map((log, i) => (
              <div className="log-entry" key={i}>
                <span className="log-time">{log.time}</span>
                <span className="log-tag tag-trade-exec">[{log.tag}]</span>
                <span className="log-msg">{log.message}</span>
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
