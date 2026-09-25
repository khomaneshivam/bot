/**
 * QuantAI Terminal - Reactive Global Trading Context
 * Central state store managing live telemetry, portfolio capital, and user actions
 */

import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import { api } from "../services/api";
import { useWebSocket } from "../hooks/useWebSocket";

const TradingContext = createContext(null);

export function TradingProvider({ children }) {
  // Navigation & Theme State
  const [activeView, setActiveView] = useState("terminal"); // "terminal" | "ledger" | "scanner" | "ai-studio" | "macro"
  const [theme, setTheme] = useState(() => localStorage.getItem("quant_theme") || "dark");

  // Core Quant Telemetry State
  const [telemetry, setTelemetry] = useState({
    symbol: "EURUSD",
    market_type: "FOREX",
    timeframe: "5m",
    is_running: true,
    account: {
      mode: "paper",
      balance: 100.0,
      equity: 100.0,
      realized_pnl: 0.0,
      unrealized_pnl: 0.0,
      win_rate: 0.0,
      total_trades: 0,
      winning_trades: 0,
      losing_trades: 0,
      profit_factor: 1.0,
      open_positions_count: 0,
      risk_vetoes_count: 0,
    },
    candles: [],
    open_positions: [],
    closed_trades: [],
    terminal_logs: [],
    dxy_proxy: 104.5,
    dxy_trend: "NEUTRAL",
    regime: "NEUTRAL",
    correlation_matrix: {},
    strategies: {},
    ml_stats: {},
    audit_matrix: null,
    latest_decision: {},
    news: null,
    psychology: null,
  });

  // Dedicated All Trades Ledger State
  const [allTradesData, setAllTradesData] = useState({
    allTrades: [],
    summary: {},
    isLoading: false,
  });

  // Theme Synchronizer
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("quant_theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  };

  // WebSocket Message Handler
  const handleWebSocketMessage = useCallback((payload) => {
    if (!payload) return;
    setTelemetry((prev) => ({
      ...prev,
      ...payload,
      account: payload.account || prev.account,
      candles: payload.candles || prev.candles,
      open_positions: payload.open_positions || prev.open_positions,
      closed_trades: payload.closed_trades || prev.closed_trades,
      terminal_logs: payload.terminal_logs || prev.terminal_logs,
      audit_matrix: payload.audit_matrix || prev.audit_matrix,
      news: payload.news !== undefined ? payload.news : prev.news,
      psychology: payload.psychology !== undefined ? payload.psychology : prev.psychology,
    }));
  }, []);

  // Initialize WebSocket Link
  const { isConnected, connectionStatus } = useWebSocket(handleWebSocketMessage);

  // Fetch initial telemetry state on mount
  useEffect(() => {
    api.getStatus()
      .then((data) => {
        if (data) handleWebSocketMessage(data);
      })
      .catch((err) => console.error("[TradingContext] Initial fetch error:", err));
  }, [handleWebSocketMessage]);

  // All Trades Ledger Fetcher
  const fetchAllTrades = useCallback(async () => {
    setAllTradesData((prev) => ({ ...prev, isLoading: true }));
    try {
      const res = await api.getAllTrades();
      if (res.status === "success") {
        const openPos = (res.open_positions || []).map((p) => ({ ...p, is_open: true }));
        const closed = (res.closed_trades || []).map((c) => ({ ...c, is_open: false }));
        setAllTradesData({
          allTrades: [...openPos, ...closed],
          summary: res.summary || {},
          isLoading: false,
        });
      }
    } catch (err) {
      console.error("[TradingContext] Error fetching all trades:", err);
      setAllTradesData((prev) => ({ ...prev, isLoading: false }));
    }
  }, []);

  // Auto-refresh ledger when switching to ledger view or when open_positions count changes
  useEffect(() => {
    if (activeView === "ledger") {
      fetchAllTrades();
    }
  }, [activeView, fetchAllTrades, telemetry.open_positions.length, telemetry.closed_trades.length]);

  // Actions
  const resetCapital = async () => {
    const confirmReset = window.confirm(
      "Reset portfolio capital back to fresh $100.00? This clears past paper trades and restores a clean ledger."
    );
    if (!confirmReset) return;

    try {
      const res = await api.resetCapital();
      if (res.status === "success") {
        await fetchAllTrades();
      }
    } catch (err) {
      console.error("[TradingContext] Reset capital error:", err);
    }
  };

  const switchMode = async (mode) => {
    if (mode === "live") {
      const confirmLive = window.confirm(
        "⚠️ CAUTION: You are switching to LIVE ACCOUNT mode. This will execute real orders with real funds. Proceed?"
      );
      if (!confirmLive) return;
    }
    await api.switchMode(mode);
  };

  const switchSymbol = async (symbol) => {
    const res = await api.switchSymbol(symbol);
    if (res.status === "success" && res.data) {
      handleWebSocketMessage(res.data);
    }
  };

  const toggleBot = async () => {
    if (telemetry.is_running) {
      await api.stopBot();
    } else {
      await api.startBot();
    }
  };

  const emergencyKill = async () => {
    const confirmKill = window.confirm(
      "🛑 EMERGENCY KILL SWITCH: Are you sure you want to close all open positions and halt the autonomous engine?"
    );
    if (confirmKill) {
      await api.emergencyStop();
      await fetchAllTrades();
    }
  };

  const placeManualTrade = async (direction) => {
    await api.placeManualTrade(direction);
  };

  const closePosition = async (positionId) => {
    await api.closePosition(positionId);
    await fetchAllTrades();
  };

  const triggerAuditScan = async () => {
    const res = await api.runAuditScan();
    if (res) {
      setTelemetry((prev) => ({ ...prev, audit_matrix: res }));
    }
  };

  const exportCSV = () => {
    api.exportTradesCSV();
  };

  const value = {
    activeView,
    setActiveView,
    theme,
    toggleTheme,
    isConnected,
    connectionStatus,
    telemetry,
    allTradesData,
    fetchAllTrades,
    resetCapital,
    switchMode,
    switchSymbol,
    toggleBot,
    emergencyKill,
    placeManualTrade,
    closePosition,
    triggerAuditScan,
    exportCSV,
  };

  return <TradingContext.Provider value={value}>{children}</TradingContext.Provider>;
}

export function useTrading() {
  const context = useContext(TradingContext);
  if (!context) {
    throw new Error("useTrading must be used within a TradingProvider");
  }
  return context;
}
