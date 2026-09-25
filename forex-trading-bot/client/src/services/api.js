/**
 * QuantAI Terminal - REST API Service Client
 * Connects React frontend directly to Python Quant Engine endpoints
 */

const API_BASE = "";

export const api = {
  // Account & Engine Telemetry
  async getStatus() {
    const res = await fetch(`${API_BASE}/api/status`);
    return res.json();
  },

  async resetCapital() {
    const res = await fetch(`${API_BASE}/api/account/reset`, { method: "POST" });
    return res.json();
  },

  // All Trades Ledger
  async getAllTrades() {
    const res = await fetch(`${API_BASE}/api/trades/all`);
    return res.json();
  },

  async getTradeDetails(tradeId) {
    const res = await fetch(`${API_BASE}/api/trade/${tradeId}`);
    return res.json();
  },

  exportTradesCSV() {
    window.location.href = `${API_BASE}/api/trades/export`;
  },

  // 1-Minute Multi-Pair Multi-Strategy Audit
  async getAuditMatrix() {
    const res = await fetch(`${API_BASE}/api/audit/matrix`);
    return res.json();
  },

  async runAuditScan() {
    const res = await fetch(`${API_BASE}/api/audit/run`, { method: "POST" });
    return res.json();
  },

  // Bot & Execution Controls
  async startBot() {
    const res = await fetch(`${API_BASE}/api/bot/start`, { method: "POST" });
    return res.json();
  },

  async stopBot() {
    const res = await fetch(`${API_BASE}/api/bot/stop`, { method: "POST" });
    return res.json();
  },

  async emergencyStop() {
    const res = await fetch(`${API_BASE}/api/emergency-stop`, { method: "POST" });
    return res.json();
  },

  async switchMode(mode) {
    const res = await fetch(`${API_BASE}/api/mode`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode }),
    });
    return res.json();
  },

  async switchSymbol(symbol) {
    const res = await fetch(`${API_BASE}/api/symbol`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol }),
    });
    return res.json();
  },

  async placeManualTrade(direction) {
    const res = await fetch(`${API_BASE}/api/trade/manual`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ direction }),
    });
    return res.json();
  },

  async closePosition(positionId) {
    const res = await fetch(`${API_BASE}/api/position/close`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ position_id: positionId }),
    });
    return res.json();
  },

  async triggerRetrain() {
    const res = await fetch(`${API_BASE}/api/retrain`, { method: "POST" });
    return res.json();
  },

  async getWrongTrades() {
    const res = await fetch(`${API_BASE}/api/wrong-trades`);
    return res.json();
  },

  // News, Gold Catalysts & Macro Radar
  async getNews() {
    const res = await fetch(`${API_BASE}/api/news`);
    return res.json();
  },

  // 20+ Year Trader Psychology & Tilt Guard
  async getPsychology() {
    const res = await fetch(`${API_BASE}/api/psychology`);
    return res.json();
  },
};
