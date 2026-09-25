/**
 * QuantAI Autonomous Forex & Crypto Trading Terminal
 * Client Controller & Real-Time Canvas Chart Engine
 */

class QuantAITerminal {
  constructor() {
    this.ws = null;
    this.reconnectTimer = null;
    this.state = null;
    this.candles = [];
    this.positions = [];
    this.crosshair = { active: false, x: 0, y: 0, candle: null };

    // DOM Elements
    this.canvas = document.getElementById("trading-chart-canvas");
    this.ctx = this.canvas.getContext("2d");
    this.tooltip = document.getElementById("chart-crosshair-tooltip");

    // Theme & Audit Initialization
    this.currentTheme = localStorage.getItem("quant_theme") || "dark";
    this.applyTheme(this.currentTheme);
    this.auditCountdown = 60;
    this.auditTickerInterval = null;

    // Multi-View Navigation & Ledger State
    this.currentView = "terminal";
    this.allTradesCache = [];
    this.currentLedgerFilter = "all";
    this.ledgerSearchQuery = "";

    this.initNavigation();
    this.initEventListeners();
    this.initCanvas();
    this.connectWebSocket();
    this.startAuditTicker();
    this.fetchAuditMatrix();
    this.fetchAndRenderAllTrades();
  }

  /* ==========================================================================
     WebSocket Telemetry Stream & Reconnection
     ========================================================================== */
  connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host || "localhost:8000";
    const wsUrl = `${protocol}//${host}/ws`;

    const statusPill = document.getElementById("connection-status-pill");
    const statusText = document.getElementById("connection-status-text");

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        statusPill.style.borderColor = "var(--border-glow-green)";
        statusPill.style.color = "var(--color-green)";
        statusText.innerText = "STREAM ONLINE";
        if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
      };

      this.ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          this.handleStateUpdate(payload);
        } catch (e) {
          console.error("JSON parse error from WS:", e);
        }
      };

      this.ws.onclose = () => {
        statusPill.style.borderColor = "var(--border-glow-red)";
        statusPill.style.color = "var(--color-red)";
        statusText.innerText = "OFFLINE - RETRYING";
        this.reconnectTimer = setTimeout(() => this.connectWebSocket(), 2500);
      };

      this.ws.onerror = () => {
        this.ws.close();
      };
    } catch (err) {
      console.error("WebSocket connection failure:", err);
      this.reconnectTimer = setTimeout(() => this.connectWebSocket(), 3000);
    }
  }

  /* ==========================================================================
     State Updates & HUD Refresh
     ========================================================================== */
  handleStateUpdate(data) {
    this.state = data;
    this.candles = data.candles || [];
    this.positions = data.open_positions || [];

    // 1. Update Header Controls
    this.updateHeader(data);

    // 2. Update Top Key Performance Indicators
    this.updateMetrics(data);

    // 3. Update Chart Canvas
    this.renderChart();

    // 4. Update Correlation Heatmap & DXY Macro
    this.updateCorrelation(data);

    // 5. Update Strategy Ensemble Radar
    this.updateStrategies(data);

    // 6. Update Wrong-Trades Retraining Studio
    this.updateWrongTrades(data);

    // 7. Update Positions & Trade History
    this.updateTables(data);

    // 8. Update Terminal Logs
    this.updateTerminalLogs(data.logs || []);

    // 9. Update 1-Minute Multi-Pair Multi-Strategy Audit Matrix
    if (data.audit_matrix) {
      this.updateAuditMatrix(data.audit_matrix);
    }
  }

  updateHeader(data) {
    // Mode Pills
    const activeMode = data.account.mode;
    document.querySelectorAll(".mode-pill").forEach((btn) => {
      if (btn.dataset.mode === activeMode) {
        btn.classList.add("active");
      } else {
        btn.classList.remove("active");
      }
    });

    const modeBadge = document.getElementById("account-mode-badge");
    if (activeMode === "paper") {
      modeBadge.innerText = "PAPER TRADING";
      modeBadge.className = "metric-badge badge-emerald";
    } else if (activeMode === "demo") {
      modeBadge.innerText = "DEMO ACCOUNT";
      modeBadge.className = "metric-badge badge-cyan";
    } else {
      modeBadge.innerText = "LIVE ACCOUNT";
      modeBadge.className = "metric-badge";
      modeBadge.style.color = "var(--color-red)";
      modeBadge.style.borderColor = "var(--border-glow-red)";
    }

    // Asset Select (do not overwrite if user is actively switching or interacting)
    const select = document.getElementById("symbol-select");
    if (!this.isSwitchingSymbol && document.activeElement !== select && select.value !== data.symbol) {
      select.value = data.symbol;
    }

    // Autonomous Toggle Button
    const botBtn = document.getElementById("toggle-bot-btn");
    const botText = document.getElementById("bot-toggle-text");
    if (data.is_running) {
      botBtn.className = "glow-button btn-success";
      botText.innerText = "AUTONOMOUS: ACTIVE";
    } else {
      botBtn.className = "glow-button";
      botBtn.style.background = "rgba(255,255,255,0.08)";
      botBtn.style.color = "var(--text-muted)";
      botBtn.style.borderColor = "var(--border-subtle)";
      botText.innerText = "AUTONOMOUS: PAUSED";
    }

    // Header Display on Chart
    document.getElementById("chart-symbol-display").innerText = data.symbol;
    document.getElementById("chart-tf-display").innerText = (data.timeframe || "5M").toUpperCase();
    document.getElementById("asset-type-badge").innerText = data.market_type || "ASSET";

    if (this.candles.length > 0) {
      const lastClose = this.candles[this.candles.length - 1].close;
      document.getElementById("chart-live-price").innerText = `$${Number(lastClose).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`;
    }
  }

  updateMetrics(data) {
    const acc = data.account;

    // Equity & Unrealized
    document.getElementById("val-equity").innerText = `$${acc.equity.toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
    const unpnlBadge = document.getElementById("val-unrealized-badge");
    const unpnl = acc.unrealized_pnl;
    unpnlBadge.innerText = `${unpnl >= 0 ? "+" : ""}$${unpnl.toFixed(2)}`;
    unpnlBadge.className = unpnl >= 0 ? "pnl-badge" : "pnl-badge text-red";
    unpnlBadge.style.background = unpnl >= 0 ? "rgba(16, 185, 129, 0.12)" : "rgba(239, 68, 68, 0.12)";

    // Balance & Realized
    document.getElementById("val-balance").innerText = `$${acc.balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
    const realPnl = acc.realized_pnl;
    const realEl = document.getElementById("val-realized-pnl");
    realEl.innerText = `${realPnl >= 0 ? "+" : ""}$${realPnl.toFixed(2)}`;
    realEl.className = realPnl >= 0 ? "mono text-green" : "mono text-red";

    // Win Rate & Profit Factor
    document.getElementById("val-win-rate").innerText = `${acc.win_rate}%`;
    document.getElementById("val-profit-factor").innerText = `PF ${acc.profit_factor}`;
    document.getElementById("trades-count-badge").innerText = `${acc.total_trades} TRADES`;
    document.getElementById("win-rate-progress-bar").style.width = `${Math.min(acc.win_rate, 100)}%`;
    document.getElementById("val-win-count").innerText = acc.winning_trades;
    document.getElementById("val-loss-count").innerText = acc.losing_trades;

    // Sidebar Account Box & Nav Badges
    const sbBal = document.getElementById("sidebar-balance-display");
    if (sbBal) sbBal.innerText = `$${acc.balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
    const sbEq = document.getElementById("sidebar-equity-display");
    if (sbEq) sbEq.innerText = `$${acc.equity.toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
    const sbPnl = document.getElementById("sidebar-realized-pnl-display");
    if (sbPnl) {
      sbPnl.innerText = `${realPnl >= 0 ? "+" : ""}$${realPnl.toFixed(2)}`;
      sbPnl.className = realPnl >= 0 ? "mono text-green" : "mono text-red";
    }
    const sbWr = document.getElementById("sidebar-winrate-display");
    if (sbWr) sbWr.innerText = `${acc.win_rate}%`;
    const sbTrades = document.getElementById("sidebar-trades-count");
    if (sbTrades) sbTrades.innerText = `${acc.total_trades}`;
    const sbMode = document.getElementById("sidebar-mode-badge");
    if (sbMode) sbMode.innerText = acc.mode ? acc.mode.toUpperCase() : "PAPER";
    const navPosBadge = document.getElementById("nav-open-positions-badge");
    if (navPosBadge) navPosBadge.innerText = `${this.positions.length} Open`;
    const navTradesBadge = document.getElementById("nav-total-trades-badge");
    if (navTradesBadge) navTradesBadge.innerText = `${acc.total_trades}`;

    // Market Regime
    const regimeEl = document.getElementById("val-market-regime");
    regimeEl.innerText = data.regime.replace(/_/g, " ");
    if (data.regime.includes("BULL")) {
      regimeEl.style.color = "var(--color-green)";
    } else if (data.regime.includes("BEAR")) {
      regimeEl.style.color = "var(--color-red)";
    } else if (data.regime.includes("VOLATILITY")) {
      regimeEl.style.color = "var(--color-yellow)";
    } else {
      regimeEl.style.color = "var(--color-cyan)";
    }

    // AI Brain
    const ml = data.ml_stats;
    document.getElementById("val-ai-params").innerText = Number(ml.parameters_count || 45000).toLocaleString();
    document.getElementById("val-mistakes-count").innerText = ml.wrong_trades_memorized || 0;
    document.getElementById("val-vetoed-count").innerText = ml.vetoed_trades_count || 0;

    // Autonomous Decision Banner
    const dec = data.latest_decision || {};
    const decDot = document.getElementById("decision-indicator-dot");
    const decSig = document.getElementById("decision-signal-text");
    const decConf = document.getElementById("decision-confidence-tag");
    const decReason = document.getElementById("decision-reason-text");

    const sig = dec.signal || "HOLD";
    decSig.innerText = sig;
    decConf.innerText = `CONF ${Math.round((dec.confidence || 0) * 100)}%`;
    decReason.innerText = dec.reason || "Evaluating market regime...";

    if (sig === "BUY") {
      decDot.className = "decision-indicator signal-buy";
      decSig.className = "font-bold text-green";
    } else if (sig === "SELL") {
      decDot.className = "decision-indicator signal-sell";
      decSig.className = "font-bold text-red";
    } else {
      decDot.className = "decision-indicator";
      decSig.className = "font-bold text-muted";
    }
  }

  updateCorrelation(data) {
    const corr = data.correlation || {};
    const dxyVal = corr.dxy_value || 104.5;
    const dxyTrend = corr.dxy_trend || "NEUTRAL";
    const matrix = corr.matrix || {};

    // 1. Update DXY Pill
    const dxyValEl = document.getElementById("dxy-value-display");
    if (dxyValEl) dxyValEl.innerText = Number(dxyVal).toFixed(2);

    const dxyTrendBadge = document.getElementById("dxy-trend-badge");
    if (dxyTrendBadge) {
      dxyTrendBadge.innerText = dxyTrend.replace(/_/g, " ");
      if (dxyTrend.includes("BULLISH")) {
        dxyTrendBadge.style.color = "var(--color-green)";
        dxyTrendBadge.style.background = "rgba(16, 185, 129, 0.15)";
      } else if (dxyTrend.includes("BEARISH")) {
        dxyTrendBadge.style.color = "var(--color-red)";
        dxyTrendBadge.style.background = "rgba(239, 68, 68, 0.15)";
      } else {
        dxyTrendBadge.style.color = "var(--text-secondary)";
        dxyTrendBadge.style.background = "rgba(255, 255, 255, 0.08)";
      }
    }

    // 2. Render Correlation Heatmap Table
    const container = document.getElementById("correlation-matrix-container");
    if (!container) return;

    const symbols = Object.keys(matrix);
    if (symbols.length === 0) {
      container.innerHTML = `<div class="empty-placeholder">Gathering price series for correlation matrix...</div>`;
      return;
    }

    const preferred = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSDT"];
    const displaySyms = preferred.filter(s => symbols.includes(s));
    for (const s of symbols) {
      if (displaySyms.length < 5 && !displaySyms.includes(s)) {
        displaySyms.push(s);
      }
    }

    let html = `<table class="heatmap-table"><thead><tr><th></th>`;
    for (const sym of displaySyms) {
      const shortName = sym.replace("USDT", "").replace("USD", "");
      html += `<th title="${sym}">${shortName}</th>`;
    }
    html += `</tr></thead><tbody>`;

    for (const rowSym of displaySyms) {
      const rowShort = rowSym.replace("USDT", "").replace("USD", "");
      html += `<tr><th title="${rowSym}">${rowShort}</th>`;
      for (const colSym of displaySyms) {
        const val = matrix[rowSym] ? (matrix[rowSym][colSym] ?? 0.0) : (rowSym === colSym ? 1.0 : 0.0);
        let cellClass = "cell-neutral";
        if (rowSym === colSym) {
          cellClass = "cell-pos-high";
        } else if (val >= 0.5) {
          cellClass = "cell-pos-high";
        } else if (val >= 0.15) {
          cellClass = "cell-pos-mid";
        } else if (val <= -0.5) {
          cellClass = "cell-neg-high";
        } else if (val <= -0.15) {
          cellClass = "cell-neg-mid";
        }

        const formatted = val === 1 ? "1.0" : (val >= 0 ? `+${val.toFixed(2)}` : val.toFixed(2));
        html += `<td class="heatmap-cell ${cellClass}" title="${rowSym} vs ${colSym}: ${formatted}">${formatted}</td>`;
      }
      html += `</tr>`;
    }
    html += `</tbody></table>`;
    if (container) container.innerHTML = html;
    const macroGrid = document.getElementById("macro-view-correlation-grid");
    if (macroGrid) macroGrid.innerHTML = html;
  }

  updateStrategies(data) {
    const container = document.getElementById("strategy-list-container");
    const stratData = data.strategies || {};
    const weights = stratData.weights || {};
    const stats = stratData.stats || {};

    let html = "";
    for (const [name, weight] of Object.entries(weights)) {
      const sStats = stats[name] || { wins: 0, losses: 0 };
      const barPct = Math.min(Math.round((weight / 2.0) * 100), 100);
      const cleanName = name.replace(/_/g, " ");

      html += `
        <div class="strategy-row">
          <div class="strategy-meta">
            <span class="strategy-name">${cleanName}</span>
            <span class="strategy-weight-tag">Weight: ${weight.toFixed(2)}x | W: ${sStats.wins} L: ${sStats.losses}</span>
          </div>
          <div class="strategy-meter-track">
            <div class="strategy-meter-bar" style="width: ${barPct}%;"></div>
          </div>
        </div>
      `;
    }
    container.innerHTML = html;
  }

  updateWrongTrades(data) {
    const list = document.getElementById("mistake-log-list");
    const studioFeed = document.getElementById("ai-studio-wrong-trades-feed");
    const wrongTrades = data.wrong_trades || [];

    if (list) {
      if (wrongTrades.length === 0) {
        list.innerHTML = `<div class="empty-placeholder">No failed trades recorded yet. Bot is performing with clean execution.</div>`;
      } else {
        let html = "";
        for (const wt of [...wrongTrades].reverse()) {
          html += `
            <div class="mistake-item">
              <div class="mistake-top">
                <span>Trade #${wt.id} (${wt.direction} ${wt.symbol})</span>
                <span>-$${Math.abs(wt.pnl).toFixed(2)}</span>
              </div>
              <div class="mistake-cause">
                <strong>Lesson:</strong> ${wt.loss_cause}
              </div>
              <div style="font-size: 0.65rem; color: var(--text-muted);">
                Regime: ${wt.regime} | Features re-weighted in training
              </div>
            </div>
          `;
        }
        list.innerHTML = html;
      }
    }

    if (studioFeed) {
      if (wrongTrades.length === 0) {
        studioFeed.innerHTML = `<div class="log-entry log-info"><span class="log-time">[ACTIVE]</span> Cosine Shield active. Monitoring candidate setups. Zero negative clusters recorded.</div>`;
      } else {
        let feedHtml = "";
        for (const wt of [...wrongTrades].reverse()) {
          feedHtml += `
            <div class="log-entry">
              <span class="log-time">[${wt.time ? wt.time.slice(11, 19) : "LOG"}]</span>
              <span class="log-tag tag-negative-shield">[SHIELDED]</span>
              <span class="log-msg">#${wt.id} ${wt.direction} ${wt.symbol} - Lesson: ${wt.loss_cause || "Loss pattern vector memorized"}</span>
            </div>
          `;
        }
        studioFeed.innerHTML = feedHtml;
      }
    }
  }

  updateTables(data) {
    // 1. Open Positions Table
    const posTbody = document.getElementById("positions-tbody");
    const posBadge = document.getElementById("active-positions-badge");
    posBadge.innerText = `${this.positions.length} OPEN`;

    if (this.positions.length === 0) {
      posTbody.innerHTML = `<tr><td colspan="9" class="text-center text-muted">No open positions. Autonomous engine is scanning for high-probability setups.</td></tr>`;
    } else {
      let html = "";
      for (const pos of this.positions) {
        const pnl = pos.unrealized_pnl || 0;
        const pnlClass = pnl >= 0 ? "text-green" : "text-red";
        const tagClass = pos.direction === "BUY" ? "tag-buy" : "tag-sell";

        html += `
          <tr>
            <td>#${pos.id}</td>
            <td><strong>${pos.symbol}</strong></td>
            <td><span class="${tagClass}">${pos.direction}</span></td>
            <td>${pos.size}</td>
            <td>$${Number(pos.entry_price).toFixed(4)}</td>
            <td>$${Number(pos.current_price).toFixed(4)}</td>
            <td>SL: $${pos.sl} / TP: $${pos.tp}</td>
            <td class="${pnlClass}"><strong>${pnl >= 0 ? "+" : ""}$${pnl.toFixed(2)}</strong></td>
            <td>
              <button class="btn-close-pos" onclick="window.terminal.closePosition('${pos.id}')">Close</button>
            </td>
          </tr>
        `;
      }
      posTbody.innerHTML = html;
    }

    // 2. Closed History Table
    const histTbody = document.getElementById("history-tbody");
    const hist = data.closed_trades || [];
    document.getElementById("closed-trades-badge").innerText = `${hist.length} TRADES`;

    if (hist.length === 0) {
      histTbody.innerHTML = `<tr><td colspan="11" class="text-center text-muted">No trade history recorded in ledger yet.</td></tr>`;
    } else {
      let html = "";
      for (const t of hist) {
        const pnl = t.pnl || 0;
        const pnlClass = pnl >= 0 ? "text-green" : "text-red";
        const tagClass = t.direction === "BUY" ? "tag-buy" : "tag-sell";
        const retPct = t.return_pct || 0;
        const retClass = retPct >= 0 ? "text-green" : "text-red";
        const marketType = t.market_type || (t.symbol && t.symbol.includes("USDT") ? "CRYPTO" : "FOREX");
        const isMistake = pnl < 0;
        const learnTag = isMistake 
          ? `<span style="color: var(--color-yellow); font-size: 0.68rem;" title="${t.loss_cause || 'Sample weight penalized'}">🧠 Retrained & Shielded</span>` 
          : `<span style="color: var(--color-green); font-size: 0.68rem;">✅ Profitable Setup</span>`;

        html += `
          <tr>
            <td>#${t.id}</td>
            <td><strong>${t.symbol}</strong></td>
            <td><span class="metric-badge" style="font-size:0.6rem;">${marketType}</span></td>
            <td><span class="${tagClass}">${t.direction}</span></td>
            <td>${t.strategy || "Ensemble"}</td>
            <td>$${Number(t.entry_price).toFixed(4)}</td>
            <td>$${Number(t.close_price || t.current_price).toFixed(4)}</td>
            <td class="${pnlClass}"><strong>${pnl >= 0 ? "+" : ""}$${pnl.toFixed(2)}</strong></td>
            <td class="${retClass}">${retPct >= 0 ? "+" : ""}${retPct.toFixed(2)}%</td>
            <td>${t.exit_reason || "COMPLETE"}</td>
            <td>${learnTag}</td>
          </tr>
        `;
      }
      histTbody.innerHTML = html;
    }
  }

  updateTerminalLogs(logs) {
    const term = document.getElementById("terminal-logs");
    let html = "";
    for (const log of logs) {
      let tagClass = "tag-system";
      if (log.tag === "AI") tagClass = "tag-ai";
      else if (log.tag === "AI_LEARN") tagClass = "tag-ai-learn";
      else if (log.tag === "TRADE_EXEC") tagClass = "tag-trade-exec";
      else if (log.tag === "NEGATIVE_SHIELD") tagClass = "tag-negative-shield";
      else if (log.tag === "DATA") tagClass = "tag-data";

      html += `
        <div class="log-entry">
          <span class="log-time">${log.time}</span>
          <span class="log-tag ${tagClass}">[${log.tag}]</span>
          <span class="log-msg">${log.message}</span>
        </div>
      `;
    }
    term.innerHTML = html;
  }

  /* ==========================================================================
     High-Resolution HTML5 Canvas Candlestick Chart Renderer
     ========================================================================== */
  initCanvas() {
    this.resizeCanvas = () => {
      if (!this.canvas || !this.canvas.parentElement) return;
      const rect = this.canvas.parentElement.getBoundingClientRect();
      const width = rect.width || 800;
      const height = rect.height || 380;
      if (width <= 50 || height <= 50) return;
      const dpr = window.devicePixelRatio || 1;
      this.canvas.width = width * dpr;
      this.canvas.height = height * dpr;
      if (this.ctx.resetTransform) {
        this.ctx.resetTransform();
      } else {
        this.ctx.setTransform(1, 0, 0, 1, 0, 0);
      }
      this.ctx.scale(dpr, dpr);
      this.renderChart();
    };

    window.addEventListener("resize", () => this.resizeCanvas());
    setTimeout(() => this.resizeCanvas(), 50);

    // Crosshair Interactions
    this.canvas.addEventListener("mousemove", (e) => {
      const rect = this.canvas.getBoundingClientRect();
      this.crosshair.active = true;
      this.crosshair.x = e.clientX - rect.left;
      this.crosshair.y = e.clientY - rect.top;
      this.renderChart();
    });

    this.canvas.addEventListener("mouseleave", () => {
      this.crosshair.active = false;
      this.tooltip.style.display = "none";
      this.renderChart();
    });
  }

  renderChart() {
    if (!this.canvas || !this.canvas.parentElement) return;
    const width = this.canvas.parentElement.clientWidth || 800;
    const height = this.canvas.parentElement.clientHeight || 380;
    if (width <= 50 || height <= 50) return;
    const ctx = this.ctx;

    ctx.clearRect(0, 0, width, height);

    if (!this.candles || this.candles.length === 0) {
      ctx.fillStyle = "rgba(148, 163, 184, 0.6)";
      ctx.font = "14px 'Inter', sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Loading live market candles...", width / 2, height / 2);
      return;
    }

    const padding = { top: 20, right: 70, bottom: 35, left: 15 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;
    const volumeHeight = chartHeight * 0.18;
    const priceHeight = chartHeight - volumeHeight - 15;

    // Price Bounds
    const highs = this.candles.map((c) => c.high);
    const lows = this.candles.map((c) => c.low);
    const volumes = this.candles.map((c) => c.volume);

    let maxPrice = Math.max(...highs);
    let minPrice = Math.min(...lows);
    const maxVol = Math.max(...volumes, 1);

    // Buffer
    const priceDelta = maxPrice - minPrice || 1;
    maxPrice += priceDelta * 0.05;
    minPrice -= priceDelta * 0.05;

    const count = this.candles.length;
    const candleWidth = Math.max(3, (chartWidth / count) * 0.65);
    const step = chartWidth / count;

    // Helper functions
    const getY = (val) => padding.top + (1 - (val - minPrice) / (maxPrice - minPrice)) * priceHeight;
    const getVolY = (vol) => height - padding.bottom - (vol / maxVol) * volumeHeight;

    const isLight = document.documentElement.getAttribute("data-theme") !== "dark";

    // 1. Draw Horizontal Grid Lines & Price Labels
    ctx.strokeStyle = isLight ? "rgba(226, 232, 240, 0.9)" : "rgba(255, 255, 255, 0.05)";
    ctx.lineWidth = 1;
    ctx.fillStyle = isLight ? "#475569" : "rgba(148, 163, 184, 0.7)";
    ctx.font = "10px 'JetBrains Mono', monospace";
    ctx.textAlign = "left";

    const gridLines = 5;
    for (let i = 0; i <= gridLines; i++) {
      const p = minPrice + (priceDelta / gridLines) * i;
      const y = getY(p);
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(width - padding.right, y);
      ctx.stroke();
      ctx.fillText(p.toFixed(p > 100 ? 2 : 4), width - padding.right + 8, y + 3);
    }

    // 2. Draw 20-period Moving Average
    const maPeriod = 20;
    ctx.strokeStyle = isLight ? "#2563eb" : "#00d2ff";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    let maStarted = false;

    for (let i = maPeriod - 1; i < count; i++) {
      const slice = this.candles.slice(i - maPeriod + 1, i + 1);
      const avg = slice.reduce((acc, c) => acc + c.close, 0) / maPeriod;
      const x = padding.left + i * step + step / 2;
      const y = getY(avg);

      if (!maStarted) {
        ctx.moveTo(x, y);
        maStarted = true;
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.stroke();

    // 3. Draw Candlesticks & Volume Bars
    let hoveredCandle = null;

    for (let i = 0; i < count; i++) {
      const c = this.candles[i];
      const x = padding.left + i * step + step / 2;
      const openY = getY(c.open);
      const closeY = getY(c.close);
      const highY = getY(c.high);
      const lowY = getY(c.low);

      const isBull = c.close >= c.open;
      const color = isBull ? (isLight ? "#059669" : "#00f59b") : (isLight ? "#dc2626" : "#ff3366");
      const volColor = isBull ? (isLight ? "rgba(5, 150, 105, 0.2)" : "rgba(0, 245, 155, 0.22)") : (isLight ? "rgba(220, 38, 38, 0.2)" : "rgba(255, 51, 102, 0.22)");

      // Volume Bar
      const vY = getVolY(c.volume);
      ctx.fillStyle = volColor;
      ctx.fillRect(x - candleWidth / 2, vY, candleWidth, height - padding.bottom - vY);

      // Wick
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(x, highY);
      ctx.lineTo(x, lowY);
      ctx.stroke();

      // Body
      ctx.fillStyle = color;
      const bodyTop = Math.min(openY, closeY);
      const bodyHeight = Math.max(Math.abs(closeY - openY), 1.5);
      ctx.fillRect(x - candleWidth / 2, bodyTop, candleWidth, bodyHeight);

      // Check hover
      if (this.crosshair.active && Math.abs(this.crosshair.x - x) < step / 2) {
        hoveredCandle = { ...c, x, y: closeY };
      }
    }

    // 4. Draw Active Positions Overlays (Entry, SL, TP lines)
    for (const pos of this.positions) {
      const entryY = getY(pos.entry_price);
      const slY = getY(pos.sl);
      const tpY = getY(pos.tp);

      // Entry Price Line
      ctx.strokeStyle = pos.direction === "BUY" ? "rgba(16, 185, 129, 0.9)" : "rgba(239, 68, 68, 0.9)";
      ctx.lineWidth = 1.2;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(padding.left, entryY);
      ctx.lineTo(width - padding.right, entryY);
      ctx.stroke();

      // SL Line
      ctx.strokeStyle = "rgba(239, 68, 68, 0.7)";
      ctx.beginPath();
      ctx.moveTo(padding.left, slY);
      ctx.lineTo(width - padding.right, slY);
      ctx.stroke();

      // TP Line
      ctx.strokeStyle = "rgba(16, 185, 129, 0.7)";
      ctx.beginPath();
      ctx.moveTo(padding.left, tpY);
      ctx.lineTo(width - padding.right, tpY);
      ctx.stroke();
      ctx.setLineDash([]); // Reset dash

      // Position Tag
      ctx.fillStyle = pos.direction === "BUY" ? "#10b981" : "#ef4444";
      ctx.fillText(`${pos.direction} #${pos.id}`, padding.left + 5, entryY - 4);
    }

    // 5. Draw Crosshair & Tooltip
    if (this.crosshair.active && hoveredCandle) {
      ctx.strokeStyle = "rgba(255, 255, 255, 0.25)";
      ctx.lineWidth = 1;
      ctx.setLineDash([3, 3]);

      // Vertical line
      ctx.beginPath();
      ctx.moveTo(hoveredCandle.x, padding.top);
      ctx.lineTo(hoveredCandle.x, height - padding.bottom);
      ctx.stroke();

      // Horizontal line
      ctx.beginPath();
      ctx.moveTo(padding.left, this.crosshair.y);
      ctx.lineTo(width - padding.right, this.crosshair.y);
      ctx.stroke();
      ctx.setLineDash([]);

      // Tooltip positioning
      this.tooltip.style.display = "block";
      this.tooltip.style.left = `${Math.min(hoveredCandle.x + 15, width - 180)}px`;
      this.tooltip.style.top = `${Math.max(this.crosshair.y - 60, 15)}px`;
      this.tooltip.innerHTML = `
        <div style="font-weight:700; color:var(--color-cyan); margin-bottom:4px;">${hoveredCandle.time.slice(11, 16)}</div>
        <div>O: $${hoveredCandle.open.toFixed(2)}</div>
        <div>H: $${hoveredCandle.high.toFixed(2)}</div>
        <div>L: $${hoveredCandle.low.toFixed(2)}</div>
        <div>C: $${hoveredCandle.close.toFixed(2)}</div>
        <div>Vol: ${Math.round(hoveredCandle.volume)}</div>
      `;
    } else {
      this.tooltip.style.display = "none";
    }
  }

  /* ==========================================================================
     Event Listeners & User Actions
     ========================================================================== */
  initEventListeners() {
    // Mode Switcher Pills
    document.querySelectorAll(".mode-pill").forEach((btn) => {
      btn.addEventListener("click", () => {
        const mode = btn.dataset.mode;
        if (mode === "live") {
          const confirmLive = confirm("⚠️ CAUTION: You are switching to LIVE ACCOUNT mode. This will execute real orders with real funds. Proceed?");
          if (!confirmLive) return;
        }
        this.switchMode(mode);
      });
    });

    // Asset Dropdown Selector
    document.getElementById("symbol-select").addEventListener("change", (e) => {
      this.switchSymbol(e.target.value);
    });

    // Autonomous Bot Toggle
    document.getElementById("toggle-bot-btn").addEventListener("click", () => {
      if (this.state && this.state.is_running) {
        this.stopBot();
      } else {
        this.startBot();
      }
    });

    // Manual Trade Buttons
    document.getElementById("btn-manual-buy").addEventListener("click", () => this.placeManualOrder("BUY"));
    document.getElementById("btn-manual-sell").addEventListener("click", () => this.placeManualOrder("SELL"));

    // Retrain Model Button
    document.getElementById("btn-retrain-ai").addEventListener("click", () => this.triggerRetrain());

    // Emergency Kill Switch
    document.getElementById("emergency-kill-btn").addEventListener("click", () => {
      const ok = confirm("🛑 EMERGENCY KILL SWITCH: Are you sure you want to immediately close all open positions and halt the autonomous bot?");
      if (ok) this.emergencyStop();
    });

    // Theme Toggle Button
    const themeBtn = document.getElementById("theme-toggle-btn");
    if (themeBtn) {
      themeBtn.addEventListener("click", () => this.toggleTheme());
    }

    // Force Audit Button
    const forceAuditBtn = document.getElementById("btn-force-audit");
    if (forceAuditBtn) {
      forceAuditBtn.addEventListener("click", () => this.triggerForceAudit());
    }
  }

  async switchMode(mode) {
    try {
      const resp = await fetch("/api/mode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode })
      });
      const data = await resp.json();
      console.log("Switched mode:", data);
    } catch (e) {
      console.error("Error switching mode:", e);
    }
  }

  async switchSymbol(symbol) {
    this.isSwitchingSymbol = true;

    // Immediate visual feedback on chart header
    document.getElementById("chart-symbol-display").innerText = symbol;
    const selectEl = document.getElementById("symbol-select");
    if (selectEl) selectEl.value = symbol;
    const priceEl = document.getElementById("chart-live-price");
    priceEl.innerText = `Loading ${symbol}...`;
    priceEl.style.color = "var(--color-cyan)";

    try {
      const resp = await fetch("/api/symbol", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol })
      });
      const result = await resp.json();
      if (result.status === "success" && result.data) {
        this.handleStateUpdate(result.data);
      }
    } catch (e) {
      console.error("Error switching symbol:", e);
    } finally {
      setTimeout(() => {
        this.isSwitchingSymbol = false;
      }, 400);
    }
  }

  async startBot() {
    try {
      await fetch("/api/bot/start", { method: "POST" });
    } catch (e) {
      console.error("Error starting bot:", e);
    }
  }

  async stopBot() {
    try {
      await fetch("/api/bot/stop", { method: "POST" });
    } catch (e) {
      console.error("Error stopping bot:", e);
    }
  }

  async placeManualOrder(direction) {
    try {
      const resp = await fetch("/api/trade/manual", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ direction })
      });
      const data = await resp.json();
      if (data.status === "error") {
        alert(data.message);
      }
    } catch (e) {
      console.error("Error placing manual order:", e);
    }
  }

  async closePosition(positionId) {
    try {
      await fetch("/api/position/close", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ position_id: positionId })
      });
    } catch (e) {
      console.error("Error closing position:", e);
    }
  }

  async triggerRetrain() {
    const btn = document.getElementById("btn-retrain-ai");
    btn.innerHTML = `<span class="btn-icon">⏳</span> Training...`;
    btn.disabled = true;

    try {
      const resp = await fetch("/api/retrain", { method: "POST" });
      const data = await resp.json();
      btn.innerHTML = `<span class="btn-icon">✅</span> Trained (${data.accuracy}%)`;
      setTimeout(() => {
        btn.innerHTML = `<span class="btn-icon">🧠</span> Retrain Model Now`;
        btn.disabled = false;
      }, 3000);
    } catch (e) {
      console.error("Error retraining:", e);
      btn.innerHTML = `<span class="btn-icon">❌</span> Error`;
      btn.disabled = false;
    }
  }

  async emergencyStop() {
    try {
      await fetch("/api/emergency-stop", { method: "POST" });
    } catch (e) {
      console.error("Error in emergency stop:", e);
    }
  }

  /* ==========================================================================
     White / Dark Theme Toggle
     ========================================================================== */
  toggleTheme() {
    this.currentTheme = this.currentTheme === "light" ? "dark" : "light";
    this.applyTheme(this.currentTheme);
  }

  applyTheme(theme) {
    this.currentTheme = theme;
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("quant_theme", theme);

    const icon = document.getElementById("theme-icon");
    const text = document.getElementById("theme-text");
    if (icon && text) {
      if (theme === "light") {
        icon.innerText = "☀️";
        text.innerText = "White Theme";
      } else {
        icon.innerText = "🌙";
        text.innerText = "Obsidian Terminal";
      }
    }
    this.renderChart();
  }

  /* ==========================================================================
     1-Minute Multi-Pair Multi-Strategy Audit Scanner Methods
     ========================================================================== */
  startAuditTicker() {
    if (this.auditTickerInterval) clearInterval(this.auditTickerInterval);
    this.auditTickerInterval = setInterval(() => {
      if (this.auditCountdown > 0) {
        this.auditCountdown--;
      } else {
        this.auditCountdown = 60;
        this.fetchAuditMatrix();
      }
      const el = document.getElementById("audit-countdown-val");
      if (el) el.innerText = `${this.auditCountdown}s`;
    }, 1000);
  }

  async fetchAuditMatrix() {
    try {
      const resp = await fetch("/api/audit/matrix");
      if (resp.ok) {
        const matrix = await resp.json();
        this.updateAuditMatrix(matrix);
      }
    } catch (e) {
      console.warn("Audit matrix fetch note:", e);
    }
  }

  async triggerForceAudit() {
    const btn = document.getElementById("btn-force-audit");
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `<span class="btn-icon">⏳</span> Scanning...`;
    }
    try {
      const resp = await fetch("/api/audit/run", { method: "POST" });
      if (resp.ok) {
        const matrix = await resp.json();
        this.updateAuditMatrix(matrix);
        this.auditCountdown = 60;
      }
    } catch (e) {
      console.error("Force audit error:", e);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `<span class="btn-icon">⚡</span> Run Scan Now`;
      }
    }
  }

  updateAuditMatrix(matrix) {
    if (!matrix || !matrix.audit_records) return;

    if (typeof matrix.next_audit_sec === "number") {
      this.auditCountdown = matrix.next_audit_sec;
      const el = document.getElementById("audit-countdown-val");
      if (el) el.innerText = `${this.auditCountdown}s`;
    }

    const tbody = document.getElementById("audit-matrix-tbody");
    if (!tbody) return;

    const records = matrix.audit_records;
    if (records.length === 0) {
      tbody.innerHTML = `<tr><td colspan="12" class="text-center text-muted">No audit records available yet.</td></tr>`;
      return;
    }

    let html = "";
    for (const item of records) {
      const sym = item.symbol;
      const price = Number(item.price || 0);
      const priceStr = price > 100 ? price.toFixed(2) : price.toFixed(4);
      const isCrypto = sym.includes("USDT");
      const marketTag = isCrypto 
        ? `<span class="metric-badge badge-cyan" style="font-size:0.6rem;">CRYPTO</span>` 
        : `<span class="metric-badge badge-purple" style="font-size:0.6rem;">FOREX</span>`;

      const chance = item.overall_chance_pct || 0;
      let barClass = "chance-grey";
      if (item.vetoed) barClass = "chance-red";
      else if (chance >= 65) barClass = "chance-green";
      else if (chance >= 40) barClass = "chance-yellow";

      const dirTag = item.overall_signal === "BUY" ? "🟢 BUY" : (item.overall_signal === "SELL" ? "🔴 SELL" : "⚪ HOLD");

      // Format strategies mini pills
      const strats = item.strategies || {};
      const formatStrat = (key) => {
        const s = strats[key] || { signal: "HOLD", chance_pct: 0 };
        const sig = s.signal || "HOLD";
        const c = s.chance_pct || 0;
        let pillClass = "pill-hold";
        if (sig === "BUY") pillClass = "pill-buy";
        else if (sig === "SELL") pillClass = "pill-sell";
        return `<span class="strat-mini-pill ${pillClass}">${sig} ${c}%</span>`;
      };

      html += `
        <tr>
          <td>
            <div class="audit-pair-wrap">
              <span class="audit-pair-name">${sym}</span>
              ${marketTag}
            </div>
          </td>
          <td><strong>$${priceStr}</strong></td>
          <td><span class="metric-badge" style="font-size:0.65rem;">${(item.regime || "NEUTRAL").replace(/_/g, " ")}</span></td>
          <td>
            <div class="chance-container">
              <div class="chance-header">
                <span>${dirTag}</span>
                <span>${chance}%</span>
              </div>
              <div class="chance-bar-bg">
                <div class="chance-bar-fill ${barClass}" style="width: ${chance}%;"></div>
              </div>
            </div>
          </td>
          <td>${formatStrat("Trend_Momentum")}</td>
          <td>${formatStrat("Mean_Reversion")}</td>
          <td>${formatStrat("Volatility_Breakout")}</td>
          <td>${formatStrat("Smart_Money_SMC")}</td>
          <td>${formatStrat("Correlation_Macro")}</td>
          <td>${formatStrat("AI_Deep_Predictor")}</td>
          <td><span class="${item.badge_class || 'badge-dormant'}">${item.status_text}</span></td>
          <td>
            <button class="btn-switch-chart" onclick="window.terminal.switchSymbol('${sym}')" title="Load ${sym} on main chart">
              📈 Chart
            </button>
          </td>
        </tr>
      `;
    }

    tbody.innerHTML = html;

    // Also sync the dedicated 1-min scanner view table if active
    const scannerViewTbody = document.getElementById("scanner-view-tbody");
    if (scannerViewTbody) {
      scannerViewTbody.innerHTML = html;
    }
  }

  /* ==========================================================================
     Sidebar Navigation & View Panels
     ========================================================================== */
  initNavigation() {
    document.querySelectorAll(".nav-link-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const view = btn.dataset.view;
        if (view) this.switchView(view);
      });
    });

    const resetBtn = document.getElementById("btn-reset-portfolio-capital");
    if (resetBtn) {
      resetBtn.addEventListener("click", () => this.resetPortfolioCapital());
    }
  }

  switchView(viewName) {
    this.currentView = viewName;

    document.querySelectorAll(".nav-link-btn").forEach((btn) => {
      if (btn.dataset.view === viewName) {
        btn.classList.add("active");
      } else {
        btn.classList.remove("active");
      }
    });

    document.querySelectorAll(".view-panel").forEach((panel) => {
      panel.classList.remove("active");
    });

    const targetPanel = document.getElementById(`view-panel-${viewName}`);
    if (targetPanel) {
      targetPanel.classList.add("active");
    }

    if (viewName === "ledger") {
      this.fetchAndRenderAllTrades();
    } else if (viewName === "scanner") {
      this.fetchAuditMatrix();
    } else if (viewName === "terminal") {
      setTimeout(() => {
        if (this.resizeCanvas) this.resizeCanvas();
        else this.renderChart();
      }, 50);
    }
  }

  /* ==========================================================================
     All Trades Ledger & Exhaustive Tracking
     ========================================================================== */
  async fetchAndRenderAllTrades() {
    try {
      const resp = await fetch("/api/trades/all");
      const data = await resp.json();
      if (data.status === "success") {
        const openPos = (data.open_positions || []).map(p => ({ ...p, is_open: true }));
        const closed = (data.closed_trades || []).map(c => ({ ...c, is_open: false }));
        this.allTradesCache = [...openPos, ...closed];

        // Update Ledger KPIs
        const total = this.allTradesCache.length;
        const openCount = openPos.length;
        const closedCount = closed.length;
        const wins = closed.filter(t => (t.pnl || 0) >= 0).length;
        const losses = closed.filter(t => (t.pnl || 0) < 0).length;
        const winRate = closedCount > 0 ? ((wins / closedCount) * 100).toFixed(1) : "0.0";
        const netPnl = closed.reduce((acc, t) => acc + (t.pnl || 0), 0);
        const grossProfit = closed.filter(t => (t.pnl || 0) > 0).reduce((acc, t) => acc + t.pnl, 0);
        const grossLoss = Math.abs(closed.filter(t => (t.pnl || 0) < 0).reduce((acc, t) => acc + t.pnl, 0));
        const pf = grossLoss > 0 ? (grossProfit / grossLoss).toFixed(2) : (grossProfit > 0 ? "MAX" : "1.00");

        // KPI Display
        const elTotal = document.getElementById("ledger-kpi-total-trades");
        if (elTotal) elTotal.innerText = total;
        const elSub = document.getElementById("ledger-kpi-open-closed-sub");
        if (elSub) elSub.innerText = `${openCount} Open · ${closedCount} Closed`;

        const elWr = document.getElementById("ledger-kpi-winrate");
        if (elWr) elWr.innerText = `${winRate}%`;
        const elWlSub = document.getElementById("ledger-kpi-wins-losses-sub");
        if (elWlSub) elWlSub.innerText = `${wins} Wins · ${losses} Losses`;

        const elPnl = document.getElementById("ledger-kpi-net-pnl");
        if (elPnl) {
          elPnl.innerText = `${netPnl >= 0 ? "+" : ""}$${netPnl.toFixed(2)}`;
          elPnl.className = netPnl >= 0 ? "ledger-kpi-val text-green" : "ledger-kpi-val text-red";
        }

        const elPf = document.getElementById("ledger-kpi-pf");
        if (elPf) elPf.innerText = pf;

        // Filter Counts
        const cAll = document.getElementById("count-filter-all");
        if (cAll) cAll.innerText = total;
        const cOpen = document.getElementById("count-filter-open");
        if (cOpen) cOpen.innerText = openCount;
        const cWins = document.getElementById("count-filter-wins");
        if (cWins) cWins.innerText = wins;
        const cLosses = document.getElementById("count-filter-losses");
        if (cLosses) cLosses.innerText = losses;

        // Render Table
        this.renderFilteredLedger();
      }
    } catch (err) {
      console.error("Error fetching all trades ledger:", err);
    }
  }

  filterLedger(filterType, element) {
    this.currentLedgerFilter = filterType;
    if (element) {
      document.querySelectorAll("#ledger-filter-tabs .filter-pill").forEach(p => p.classList.remove("active"));
      element.classList.add("active");
    }
    this.renderFilteredLedger();
  }

  handleLedgerSearch(query) {
    this.ledgerSearchQuery = (query || "").trim().toLowerCase();
    this.renderFilteredLedger();
  }

  renderFilteredLedger() {
    const tbody = document.getElementById("all-trades-tbody");
    if (!tbody) return;

    let items = [...this.allTradesCache];

    if (this.currentLedgerFilter === "open") {
      items = items.filter(t => t.is_open);
    } else if (this.currentLedgerFilter === "wins") {
      items = items.filter(t => !t.is_open && (t.pnl || 0) >= 0);
    } else if (this.currentLedgerFilter === "losses") {
      items = items.filter(t => !t.is_open && (t.pnl || 0) < 0);
    } else if (this.currentLedgerFilter === "forex") {
      items = items.filter(t => !(t.symbol || "").includes("USDT"));
    } else if (this.currentLedgerFilter === "crypto") {
      items = items.filter(t => (t.symbol || "").includes("USDT"));
    }

    if (this.ledgerSearchQuery) {
      const q = this.ledgerSearchQuery;
      items = items.filter(t => 
        (t.id && t.id.toLowerCase().includes(q)) ||
        (t.symbol && t.symbol.toLowerCase().includes(q)) ||
        (t.strategy && t.strategy.toLowerCase().includes(q)) ||
        (t.direction && t.direction.toLowerCase().includes(q))
      );
    }

    if (items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="13" class="text-center text-muted">No trades match the selected criteria.</td></tr>`;
      return;
    }

    let html = "";
    for (const t of items) {
      const isOpen = t.is_open;
      const statusBadge = isOpen 
        ? `<span class="status-pill-open"><span class="status-pulse-dot" style="width:6px; height:6px;"></span> ACTIVE</span>`
        : ((t.pnl || 0) >= 0 ? `<span class="status-pill-win">WIN</span>` : `<span class="status-pill-loss">LOSS</span>`);

      const pnl = isOpen ? (t.unrealized_pnl || 0) : (t.pnl || 0);
      const pnlClass = pnl >= 0 ? "text-green" : "text-red";
      const retPct = t.return_pct || 0;
      const retClass = retPct >= 0 ? "text-green" : "text-red";
      const tagClass = t.direction === "BUY" ? "tag-buy" : "tag-sell";

      const entryPrice = Number(t.entry_price || 0).toFixed(4);
      const exitPrice = isOpen ? Number(t.current_price || t.entry_price).toFixed(4) : Number(t.close_price || t.current_price).toFixed(4);
      const slTp = `SL: ${t.sl || '-'} / TP: ${t.tp || '-'}`;

      let causeHtml = `<span class="text-muted">${t.exit_reason || (isOpen ? 'In Progress' : 'COMPLETE')}</span>`;
      if (!isOpen && (t.pnl || 0) < 0) {
        causeHtml = `<span class="mistake-lesson-badge" title="${t.loss_cause || 'Pattern penalized in vector shield'}">${t.loss_cause || 'Cosine Shield Active'}</span>`;
      }

      const timeStr = t.open_time || t.close_time || "-";

      html += `
        <tr>
          <td>${statusBadge}</td>
          <td><strong>#${t.id}</strong></td>
          <td>
            <strong>${t.symbol}</strong>
            <span class="metric-badge" style="font-size:0.55rem; margin-left:4px;">${(t.symbol || "").includes("USDT") ? "CRYPTO" : "FOREX"}</span>
          </td>
          <td><span class="${tagClass}">${t.direction}</span></td>
          <td>${t.size}</td>
          <td>$${entryPrice}</td>
          <td>$${exitPrice}</td>
          <td style="font-size:0.75rem;">${slTp}</td>
          <td class="${pnlClass}"><strong>${pnl >= 0 ? "+" : ""}$${pnl.toFixed(2)}</strong></td>
          <td class="${retClass}">${retPct >= 0 ? "+" : ""}${retPct.toFixed(2)}%</td>
          <td><span class="metric-badge" style="font-size:0.65rem;">${t.strategy || "Ensemble"}</span></td>
          <td>${causeHtml}</td>
          <td style="font-size:0.72rem; color:var(--text-muted);">${timeStr}</td>
        </tr>
      `;
    }

    tbody.innerHTML = html;
  }

  exportTradesCSV() {
    window.location.href = "/api/trades/export";
  }

  async resetPortfolioCapital() {
    const confirmReset = confirm("Reset paper trading capital back to fresh $100.00? This clears past paper trades and restores a clean ledger.");
    if (!confirmReset) return;

    try {
      const resp = await fetch("/api/account/reset", { method: "POST" });
      const data = await resp.json();
      if (data.status === "success") {
        this.fetchAndRenderAllTrades();
        alert("Portfolio capital reset to $100.00.");
      }
    } catch (e) {
      console.error("Error resetting capital:", e);
    }
  }
}

// Instantiate terminal when DOM loads
window.addEventListener("DOMContentLoaded", () => {
  window.terminal = new QuantAITerminal();
});
