/**
 * QuantAI Institutional Trading Terminal - System Constants
 */

export const EXECUTION_MODES = {
  PAPER: {
    key: "paper",
    label: "PAPER TRADING",
    shortLabel: "PAPER",
    description: "Simulated execution with $100 starting capital and persistent ledger",
    variant: "emerald",
    isLive: false,
    badgeText: "PAPER",
  },
  MT5_DEMO: {
    key: "demo",
    label: "MT5 DEMO",
    shortLabel: "MT5 DEMO",
    description: "MetaTrader 5 demo server execution with simulated liquidity",
    variant: "cyan",
    isLive: false,
    badgeText: "MT5 DEMO",
  },
  BINANCE_TESTNET: {
    key: "binance_testnet",
    label: "BINANCE TESTNET",
    shortLabel: "BINANCE TESTNET",
    description: "Binance Spot/Futures testnet sandbox execution",
    variant: "cyan",
    isLive: false,
    badgeText: "BINANCE TESTNET",
  },
  MT5_LIVE: {
    key: "live",
    label: "MT5 LIVE REAL CAPITAL",
    shortLabel: "MT5 LIVE",
    description: "Live broker execution with real capital risk. Requires authorized approval.",
    variant: "rose",
    isLive: true,
    badgeText: "MT5 LIVE",
  },
  BINANCE_LIVE: {
    key: "binance_live",
    label: "BINANCE LIVE CAPITAL",
    shortLabel: "BINANCE LIVE",
    description: "Live cryptocurrency exchange execution. Real funds at risk.",
    variant: "rose",
    isLive: true,
    badgeText: "BINANCE LIVE",
  },
};

export const ORDER_STATUSES = {
  CREATED: { label: "CREATED", color: "blue", step: 1 },
  RISK_APPROVED: { label: "RISK APPROVED", color: "cyan", step: 2 },
  SUBMITTED: { label: "SUBMITTED", color: "amber", step: 3 },
  ACKNOWLEDGED: { label: "ACKNOWLEDGED", color: "purple", step: 4 },
  PARTIALLY_FILLED: { label: "PARTIAL FILL", color: "amber", step: 5 },
  FILLED: { label: "FILLED", color: "emerald", step: 6 },
  REJECTED: { label: "REJECTED", color: "rose", step: 0 },
  CANCELLED: { label: "CANCELLED", color: "slate", step: 0 },
  UNKNOWN: { label: "UNKNOWN STATUS", color: "rose", step: 0, critical: true },
  RECONCILIATION_REQUIRED: { label: "RECONCILIATION REQUIRED", color: "rose", step: 0, critical: true },
};

export const RISK_LEVELS = {
  SAFE: { label: "SAFE", color: "emerald", description: "All 9 risk gates cleared. Execution permitted." },
  WARNING: { label: "WARNING", color: "amber", description: "Elevated volatility or approaching limits." },
  BLOCKED: { label: "BLOCKED", color: "rose", description: "New entries halted by deterministic safety gates." },
};

export const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: "LayoutDashboard", description: "Executive operations & high-level telemetry" },
  { id: "markets", label: "Markets", icon: "CandlestickChart", description: "Market chart & calibrated signal decision engine" },
  { id: "positions", label: "Positions", icon: "Layers", description: "Active positions with broker truth reconciliation" },
  { id: "orders", label: "Orders", icon: "FileText", description: "Deterministic order state-machine lifecycle" },
  { id: "strategies", label: "Strategies", icon: "Compass", description: "Ensemble attribution & regime correlation matrix" },
  { id: "ml", label: "AI / ML", icon: "Cpu", description: "Champion/Challenger registry & calibration observability" },
  { id: "risk", label: "Risk Engine", icon: "ShieldAlert", description: "9 deterministic risk gates & circuit breaker status" },
  { id: "news", label: "News & Macro", icon: "Globe", description: "Scheduled blackout windows & live catalyst feeds" },
  { id: "execution", label: "Execution", icon: "Zap", description: "Broker execution latency, fill rates & slippage metrics" },
  { id: "reconciliation", label: "Reconciliation", icon: "Scale", description: "Internal vs broker position discrepancy console" },
  { id: "system", label: "System Health", icon: "Server", description: "Infrastructure, Prometheus telemetry & host status" },
  { id: "audit", label: "Audit Log", icon: "History", description: "Immutable chronological security & operations history" },
];
