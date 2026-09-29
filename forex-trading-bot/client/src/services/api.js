/**
 * QuantAI Terminal - REST API Service Client
 * Connects React frontend directly to Python Quant Engine endpoints with RBAC & status validation
 */

const API_BASE = "";

const getHeaders = (extra = {}) => {
  const token = typeof localStorage !== "undefined" ? localStorage.getItem("quant_auth_token") : null;
  return {
    ...extra,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
};

async function handleResponse(res) {
  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}: ${res.statusText}`;
    try {
      const errJson = await res.json();
      if (errJson && errJson.detail) {
        errorDetail = errJson.detail;
      }
    } catch {
      // response wasn't JSON
    }
    const err = new Error(errorDetail);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export const api = {
  // Authentication & RBAC
  async login(username, password) {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    return handleResponse(res);
  },

  async register({ username, password, confirmPassword, role, adminKey }) {
    const res = await fetch(`${API_BASE}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username,
        password,
        confirm_password: confirmPassword,
        role: role || "TRADER",
        admin_key: adminKey || null,
      }),
    });
    return handleResponse(res);
  },

  async logout() {
    try {
      await fetch(`${API_BASE}/api/auth/logout`, {
        method: "POST",
        headers: getHeaders(),
      });
    } catch {
      // Ignore network errors during logout
    }
  },

  async getMe() {
    const res = await fetch(`${API_BASE}/api/auth/me`, { headers: getHeaders() });
    return handleResponse(res);
  },

  async changePassword({ oldPassword, newPassword, confirmPassword }) {
    const res = await fetch(`${API_BASE}/api/auth/change-password`, {
      method: "POST",
      headers: getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        old_password: oldPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      }),
    });
    return handleResponse(res);
  },

  // Account & Engine Telemetry
  async getStatus() {
    const res = await fetch(`${API_BASE}/api/status`, { headers: getHeaders() });
    return handleResponse(res);
  },

  async resetCapital() {
    const res = await fetch(`${API_BASE}/api/account/reset`, { method: "POST", headers: getHeaders() });
    return handleResponse(res);
  },

  // Orders State-Machine Lifecycle
  async getOrders() {
    const res = await fetch(`${API_BASE}/api/orders`, { headers: getHeaders() });
    return handleResponse(res);
  },

  // All Trades Ledger & Historical Records
  async getAllTrades() {
    const res = await fetch(`${API_BASE}/api/trades/all`, { headers: getHeaders() });
    return handleResponse(res);
  },

  async getTradeDetails(tradeId) {
    const res = await fetch(`${API_BASE}/api/trade/${tradeId}`, { headers: getHeaders() });
    return handleResponse(res);
  },

  exportTradesCSV() {
    window.location.href = `${API_BASE}/api/trades/export`;
  },

  // Risk & Circuit Breakers
  async getRiskStatus() {
    const res = await fetch(`${API_BASE}/api/risk/status`, { headers: getHeaders() });
    return handleResponse(res);
  },

  async resetCircuitBreakers() {
    const res = await fetch(`${API_BASE}/api/circuit-breakers/reset`, { method: "POST", headers: getHeaders() });
    return handleResponse(res);
  },

  // Broker Reconciliation Console
  async getReconciliationStatus() {
    const res = await fetch(`${API_BASE}/api/reconciliation/status`, { headers: getHeaders() });
    return handleResponse(res);
  },

  async triggerReconciliation() {
    const res = await fetch(`${API_BASE}/api/reconcile`, { method: "POST", headers: getHeaders() });
    return handleResponse(res);
  },

  // AI / ML Observability & Model Registry
  async getModels() {
    const res = await fetch(`${API_BASE}/api/models`, { headers: getHeaders() });
    return handleResponse(res);
  },

  async triggerRetrain() {
    const res = await fetch(`${API_BASE}/api/retrain`, { method: "POST", headers: getHeaders() });
    return handleResponse(res);
  },

  async getWrongTrades() {
    const res = await fetch(`${API_BASE}/api/wrong-trades`, { headers: getHeaders() });
    return handleResponse(res);
  },

  // News & Macro Feeds
  async getNews() {
    const res = await fetch(`${API_BASE}/api/news`, { headers: getHeaders() });
    return handleResponse(res);
  },

  // Trader Psychology & Tilt Guard
  async getPsychology() {
    const res = await fetch(`${API_BASE}/api/psychology`, { headers: getHeaders() });
    return handleResponse(res);
  },

  // 1-Minute Multi-Pair Multi-Strategy Audit
  async getAuditMatrix() {
    const res = await fetch(`${API_BASE}/api/audit/matrix`, { headers: getHeaders() });
    return handleResponse(res);
  },

  async runAuditScan() {
    const res = await fetch(`${API_BASE}/api/audit/run`, { method: "POST", headers: getHeaders() });
    return handleResponse(res);
  },

  // Immutable Audit Log History
  async getAuditLogs(limit = 150) {
    const res = await fetch(`${API_BASE}/api/audit/logs?limit=${limit}`, { headers: getHeaders() });
    return handleResponse(res);
  },

  // System Telemetry & Infrastructure Health
  async getSystemHealth() {
    const res = await fetch(`${API_BASE}/api/system/health`, { headers: getHeaders() });
    return handleResponse(res);
  },

  // Bot & Execution Controls
  async startBot() {
    const res = await fetch(`${API_BASE}/api/bot/start`, { method: "POST", headers: getHeaders() });
    return handleResponse(res);
  },

  async stopBot() {
    const res = await fetch(`${API_BASE}/api/bot/stop`, { method: "POST", headers: getHeaders() });
    return handleResponse(res);
  },

  async emergencyStop() {
    const res = await fetch(`${API_BASE}/api/emergency-stop`, { method: "POST", headers: getHeaders() });
    return handleResponse(res);
  },

  async switchMode(mode) {
    const res = await fetch(`${API_BASE}/api/mode`, {
      method: "POST",
      headers: getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ mode }),
    });
    return handleResponse(res);
  },

  async switchSymbol(symbol) {
    const res = await fetch(`${API_BASE}/api/symbol`, {
      method: "POST",
      headers: getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ symbol }),
    });
    return handleResponse(res);
  },

  async placeManualTrade(direction) {
    const res = await fetch(`${API_BASE}/api/trade/manual`, {
      method: "POST",
      headers: getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ direction }),
    });
    return handleResponse(res);
  },

  async closePosition(positionId) {
    const res = await fetch(`${API_BASE}/api/position/close`, {
      method: "POST",
      headers: getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ position_id: positionId }),
    });
    return handleResponse(res);
  },
};
