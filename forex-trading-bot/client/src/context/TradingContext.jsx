import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import { api } from "../services/api";
import { useWebSocket } from "../hooks/useWebSocket";

const TradingContext = createContext(null);

export function TradingProvider({ children }) {
  // Navigation State - Supports 12 First-Class Views
  const [activeView, setActiveView] = useState("dashboard");
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const toggleSidebar = () => setIsSidebarCollapsed((prev) => !prev);

  // Safe Action Confirmation Modal State
  const [confirmModal, setConfirmModal] = useState({
    isOpen: false,
    title: "",
    description: "",
    warningNote: "",
    confirmWord: null,
    confirmVariant: "danger",
    checklist: [],
    onConfirm: () => {},
  });

  // Core Real-Time Telemetry State
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
      daily_drawdown_limit_hit: false,
      risk_vetoes_count: 0,
    },
    candles: [],
    open_positions: [],
    closed_trades: [],
    wrong_trades: [],
    logs: [],
    regime: "NEUTRAL",
    correlation: {},
    strategies: {},
    ml_stats: {},
    latest_decision: {},
    audit_matrix: null,
    news: null,
    psychology: null,
    circuit_breakers: { tripped: false, active_breakers: {}, trip_timestamps: {} },
    broker_connected: true,
    feed_fresh: true,
  });

  // Dedicated View States
  const [ordersData, setOrdersData] = useState({ orders: [], transitions: [], isLoading: false });
  const [reconciliationData, setReconciliationData] = useState({
    report: null,
    has_active_mismatch: false,
    internal_positions: [],
    broker_positions: [],
    isLoading: false,
  });
  const [riskData, setRiskData] = useState({ status: null, isLoading: false });
  const [modelsData, setModelsData] = useState({ champion: null, challenger: null, models: [], stats: {}, isLoading: false });
  const [auditLogsData, setAuditLogsData] = useState({ events: [], isLoading: false });
  const [systemHealthData, setSystemHealthData] = useState({ health: null, isLoading: false });
  const [allTradesData, setAllTradesData] = useState({ allTrades: [], summary: {}, isLoading: false });

  // WebSocket Message Handler
  const handleWebSocketMessage = useCallback((payload) => {
    if (!payload) return;
    setTelemetry((prev) => ({
      ...prev,
      ...payload,
      account: payload.account ? { ...prev.account, ...payload.account } : prev.account,
      candles: payload.candles || prev.candles,
      open_positions: payload.open_positions !== undefined ? payload.open_positions : prev.open_positions,
      closed_trades: payload.closed_trades !== undefined ? payload.closed_trades : prev.closed_trades,
      circuit_breakers: payload.circuit_breakers || prev.circuit_breakers,
      broker_connected: payload.broker_connected !== undefined ? payload.broker_connected : prev.broker_connected,
      feed_fresh: payload.feed_fresh !== undefined ? payload.feed_fresh : prev.feed_fresh,
    }));
  }, []);

  // Initialize WebSocket Link
  const authToken = typeof localStorage !== "undefined" ? localStorage.getItem("quant_auth_token") : null;
  const { isConnected, connectionStatus, lastMessageTime, latencyMs } = useWebSocket(handleWebSocketMessage, authToken);

  // Fetch initial telemetry state on mount
  useEffect(() => {
    api.getStatus()
      .then((data) => {
        if (data) handleWebSocketMessage(data);
      })
      .catch((err) => console.warn("[TradingContext] Initial fetch error:", err));
  }, [handleWebSocketMessage]);

  // View Data Fetchers
  const fetchOrders = useCallback(async () => {
    setOrdersData((prev) => ({ ...prev, isLoading: true }));
    try {
      const res = await api.getOrders();
      if (res && res.orders) {
        setOrdersData({ orders: res.orders, transitions: res.transitions || [], isLoading: false });
      }
    } catch (err) {
      console.error("[TradingContext] Error fetching orders:", err);
      setOrdersData((prev) => ({ ...prev, isLoading: false }));
    }
  }, []);

  const fetchReconciliation = useCallback(async () => {
    setReconciliationData((prev) => ({ ...prev, isLoading: true }));
    try {
      const res = await api.getReconciliationStatus();
      if (res) {
        setReconciliationData({
          report: res.report,
          has_active_mismatch: res.has_active_mismatch,
          internal_positions: res.internal_positions || [],
          broker_positions: res.broker_positions || [],
          isLoading: false,
        });
      }
    } catch (err) {
      console.error("[TradingContext] Error fetching reconciliation:", err);
      setReconciliationData((prev) => ({ ...prev, isLoading: false }));
    }
  }, []);

  const fetchRiskStatus = useCallback(async () => {
    setRiskData((prev) => ({ ...prev, isLoading: true }));
    try {
      const res = await api.getRiskStatus();
      if (res) {
        setRiskData({ status: res, isLoading: false });
      }
    } catch (err) {
      console.error("[TradingContext] Error fetching risk status:", err);
      setRiskData((prev) => ({ ...prev, isLoading: false }));
    }
  }, []);

  const fetchModels = useCallback(async () => {
    setModelsData((prev) => ({ ...prev, isLoading: true }));
    try {
      const res = await api.getModels();
      if (res) {
        setModelsData({
          champion: res.champion,
          challenger: res.challenger,
          models: res.models || [],
          stats: res.stats || {},
          isLoading: false,
        });
      }
    } catch (err) {
      console.error("[TradingContext] Error fetching models:", err);
      setModelsData((prev) => ({ ...prev, isLoading: false }));
    }
  }, []);

  const fetchAuditLogs = useCallback(async () => {
    setAuditLogsData((prev) => ({ ...prev, isLoading: true }));
    try {
      const res = await api.getAuditLogs(150);
      if (res && res.events) {
        setAuditLogsData({ events: res.events, isLoading: false });
      }
    } catch (err) {
      console.error("[TradingContext] Error fetching audit logs:", err);
      setAuditLogsData((prev) => ({ ...prev, isLoading: false }));
    }
  }, []);

  const fetchSystemHealth = useCallback(async () => {
    setSystemHealthData((prev) => ({ ...prev, isLoading: true }));
    try {
      const res = await api.getSystemHealth();
      if (res) {
        setSystemHealthData({ health: res, isLoading: false });
      }
    } catch (err) {
      console.error("[TradingContext] Error fetching system health:", err);
      setSystemHealthData((prev) => ({ ...prev, isLoading: false }));
    }
  }, []);

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

  // Fetch view-specific data when navigating
  useEffect(() => {
    if (activeView === "orders") fetchOrders();
    if (activeView === "reconciliation") fetchReconciliation();
    if (activeView === "risk") fetchRiskStatus();
    if (activeView === "ml") fetchModels();
    if (activeView === "audit") fetchAuditLogs();
    if (activeView === "system") fetchSystemHealth();
    if (activeView === "positions") fetchAllTrades();
  }, [activeView, fetchOrders, fetchReconciliation, fetchRiskStatus, fetchModels, fetchAuditLogs, fetchSystemHealth, fetchAllTrades]);

  // Confirmation Modal Open Helper
  const openConfirmModal = ({
    title,
    description,
    warningNote,
    confirmWord,
    confirmVariant = "danger",
    checklist = [],
    action,
  }) => {
    setConfirmModal({
      isOpen: true,
      title,
      description,
      warningNote,
      confirmWord,
      confirmVariant,
      checklist,
      onConfirm: async () => {
        setConfirmModal((prev) => ({ ...prev, isOpen: false }));
        if (action) await action();
      },
    });
  };

  const closeConfirmModal = () => {
    setConfirmModal((prev) => ({ ...prev, isOpen: false }));
  };

  // Safe Actions
  const switchModeSafe = (targetMode) => {
    const isLive = targetMode.toLowerCase().includes("live");

    const checklist = [
      { label: "Broker Connected & Healthy", ok: Boolean(telemetry.broker_connected) },
      { label: "Market Data Fresh", ok: Boolean(telemetry.feed_fresh) },
      { label: "Risk Circuit Breakers Normal", ok: !telemetry.circuit_breakers?.tripped },
      { label: "Reconciliation Synchronized", ok: !reconciliationData.has_active_mismatch },
    ];

    openConfirmModal({
      title: isLive ? "SWITCH TO LIVE REAL-MONEY MODE" : `Switch Execution Mode to ${targetMode.toUpperCase()}`,
      description: isLive
        ? "You are about to switch the execution engine to LIVE REAL CAPITAL. Real broker orders will be submitted with real funds at risk. This operation requires full operator accountability."
        : `Switch execution mode to ${targetMode.toUpperCase()}. This will re-initialize the execution adapter.`,
      warningNote: isLive ? "CRITICAL RISK: Real funds at risk. Ensure all risk limits and broker accounts are verified." : null,
      confirmWord: isLive ? "LIVE" : null,
      confirmVariant: isLive ? "danger" : "warning",
      checklist: isLive ? checklist : [],
      action: async () => {
        try {
          await api.switchMode(targetMode);
          await api.getStatus().then((d) => d && handleWebSocketMessage(d));
        } catch (err) {
          alert(`Mode switch failed: ${err.message}`);
        }
      },
    });
  };

  const resetCapitalSafe = () => {
    openConfirmModal({
      title: "RESET PORTFOLIO CAPITAL BACK TO $100.00",
      description: "This administrative operation resets the starting capital pool back to $100.00. Past paper trade ledgers will be reset to zero baseline.",
      warningNote: "Requires Administrator authorization. Clears paper trading performance history.",
      confirmWord: "RESET",
      confirmVariant: "danger",
      checklist: [{ label: "Autonomous Bot Active", ok: true }],
      action: async () => {
        try {
          await api.resetCapital();
          await fetchAllTrades();
          await api.getStatus().then((d) => d && handleWebSocketMessage(d));
        } catch (err) {
          alert(`Capital reset failed: ${err.message}`);
        }
      },
    });
  };

  const emergencyKillSafe = () => {
    openConfirmModal({
      title: "🛑 EMERGENCY KILL SWITCH: HALT & LIQUIDATE",
      description: "Instantly halt the autonomous trading bot, liquidate all open positions at market, and trip the EMERGENCY_STOP circuit breaker.",
      warningNote: "This will immediately close all active positions and block all new entries until manually reset.",
      confirmWord: "HALT",
      confirmVariant: "danger",
      checklist: [],
      action: async () => {
        try {
          await api.emergencyStop();
          await fetchAllTrades();
          await api.getStatus().then((d) => d && handleWebSocketMessage(d));
        } catch (err) {
          alert(`Emergency stop failed: ${err.message}`);
        }
      },
    });
  };

  const toggleBotSafe = () => {
    const nextState = !telemetry.is_running;
    openConfirmModal({
      title: nextState ? "START AUTONOMOUS TRADING BOT" : "PAUSE AUTONOMOUS TRADING BOT",
      description: nextState
        ? "Resume the autonomous trading engine. New setups matching deterministic risk and ML criteria will be submitted."
        : "Pause the autonomous trading engine. Existing open positions will continue to be monitored for SL/TP, but no new trades will be opened.",
      confirmVariant: nextState ? "warning" : "danger",
      action: async () => {
        try {
          if (nextState) await api.startBot();
          else await api.stopBot();
          await api.getStatus().then((d) => d && handleWebSocketMessage(d));
        } catch (err) {
          alert(`Bot toggle failed: ${err.message}`);
        }
      },
    });
  };

  const closePositionSafe = (positionId, symbol) => {
    openConfirmModal({
      title: `CLOSE POSITION #${positionId} (${symbol})`,
      description: `Submit immediate market exit for position #${positionId}. This will close the trade and realize current floating P&L.`,
      confirmVariant: "warning",
      action: async () => {
        try {
          await api.closePosition(positionId);
          await fetchAllTrades();
          await api.getStatus().then((d) => d && handleWebSocketMessage(d));
        } catch (err) {
          alert(`Failed to close position: ${err.message}`);
        }
      },
    });
  };

  const placeManualTradeSafe = (direction) => {
    const symbol = telemetry.symbol;
    openConfirmModal({
      title: `SUBMIT MANUAL ${direction} ON ${symbol}`,
      description: `Privileged manual execution: Submit market ${direction} for ${symbol} evaluated against all 9 deterministic risk gates.`,
      warningNote: telemetry.account.mode === "live" ? "CAUTION: This will place a real-money order." : null,
      confirmVariant: telemetry.account.mode === "live" ? "danger" : "primary",
      checklist: [
        { label: "Risk Circuit Breakers Normal", ok: !telemetry.circuit_breakers?.tripped },
        { label: "Broker Connected", ok: Boolean(telemetry.broker_connected) },
      ],
      action: async () => {
        try {
          const res = await api.placeManualTrade(direction);
          if (res.status === "error") {
            alert(`Order rejected: ${res.message}`);
          }
          await fetchAllTrades();
          await api.getStatus().then((d) => d && handleWebSocketMessage(d));
        } catch (err) {
          alert(`Trade execution failed: ${err.message}`);
        }
      },
    });
  };

  const triggerRetrainSafe = () => {
    openConfirmModal({
      title: "TRIGGER MODEL WALK-FORWARD RETRAINING",
      description: "Initiates walk-forward validation and Platt probability calibration across the historical market dataset.",
      confirmVariant: "warning",
      action: async () => {
        try {
          const res = await api.triggerRetrain();
          alert(`Retrain completed: ${res.message || "Model weights updated"}`);
          await fetchModels();
        } catch (err) {
          alert(`Retrain failed: ${err.message}`);
        }
      },
    });
  };

  const resetCircuitBreakersSafe = () => {
    openConfirmModal({
      title: "ADMINISTRATIVE RESET OF CIRCUIT BREAKERS",
      description: "Clears all tripped circuit breakers and unlocks new trade entry. Only perform this after verifying the root cause of the risk trip.",
      warningNote: "Ensure market data feeds and broker accounts are fully healthy before resuming.",
      confirmVariant: "danger",
      action: async () => {
        try {
          await api.resetCircuitBreakers();
          await fetchRiskStatus();
          await api.getStatus().then((d) => d && handleWebSocketMessage(d));
        } catch (err) {
          alert(`Circuit breaker reset failed: ${err.message}`);
        }
      },
    });
  };

  const switchSymbol = async (symbol) => {
    try {
      const res = await api.switchSymbol(symbol);
      if (res.status === "success" && res.data) {
        handleWebSocketMessage(res.data);
      }
    } catch (err) {
      console.error("[TradingContext] Symbol switch error:", err);
    }
  };

  const value = {
    activeView,
    setActiveView,
    isSidebarCollapsed,
    toggleSidebar,
    isConnected,
    connectionStatus,
    lastMessageTime,
    latencyMs,
    telemetry,
    ordersData,
    reconciliationData,
    riskData,
    modelsData,
    auditLogsData,
    systemHealthData,
    allTradesData,
    confirmModal,
    openConfirmModal,
    closeConfirmModal,
    switchModeSafe,
    resetCapitalSafe,
    emergencyKillSafe,
    toggleBotSafe,
    closePositionSafe,
    placeManualTradeSafe,
    triggerRetrainSafe,
    resetCircuitBreakersSafe,
    switchSymbol,
    fetchOrders,
    fetchReconciliation,
    fetchRiskStatus,
    fetchModels,
    fetchAuditLogs,
    fetchSystemHealth,
    fetchAllTrades,
    exportCSV: api.exportTradesCSV,
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
