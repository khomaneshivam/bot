/**
 * QuantAI Terminal - Quantitative Data Formatters & Math Utilities
 */

export const formatCurrency = (val, decimals = 2) => {
  const num = Number(val) || 0;
  return `$${num.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}`;
};

export const formatPrice = (val, symbol = "") => {
  const num = Number(val) || 0;
  const sym = String(symbol).toUpperCase();
  const isCrypto = sym.includes("USDT") || sym.includes("BTC") || sym.includes("ETH") || sym.includes("SOL");
  const isGold = sym.includes("XAU") || sym.includes("GOLD");

  if (isCrypto && num > 100) {
    return num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  if (isGold) {
    return num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  if (sym.includes("JPY")) {
    return num.toFixed(3);
  }
  return num.toFixed(5);
};

export const formatPnL = (val, prefix = "$") => {
  const num = Number(val) || 0;
  const sign = num > 0 ? "+" : num < 0 ? "-" : "";
  return `${sign}${prefix}${Math.abs(num).toFixed(2)}`;
};

export const formatPercent = (val) => {
  const num = Number(val) || 0;
  const sign = num > 0 ? "+" : "";
  return `${sign}${num.toFixed(2)}%`;
};

export const formatRMultiple = (pnl, riskAmount) => {
  const p = Number(pnl) || 0;
  const r = Number(riskAmount) || 1.0;
  if (r <= 0) return `${p >= 0 ? "+" : ""}${p.toFixed(2)}R`;
  const ratio = p / r;
  return `${ratio >= 0 ? "+" : ""}${ratio.toFixed(2)}R`;
};

export const getPnLTextColor = (val) => {
  const num = Number(val) || 0;
  if (num > 0) return "text-emerald-400";
  if (num < 0) return "text-rose-400";
  return "text-slate-400";
};

export const getPnLBgColor = (val) => {
  const num = Number(val) || 0;
  if (num > 0) return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
  if (num < 0) return "bg-rose-500/10 text-rose-400 border-rose-500/30";
  return "bg-slate-800 text-slate-300 border-slate-700";
};

export const formatTimeAgo = (timestamp) => {
  if (!timestamp) return "N/A";
  const now = Date.now();
  const past = new Date(timestamp).getTime();
  if (isNaN(past)) return String(timestamp).slice(11, 19);

  const diffSec = Math.floor((now - past) / 1000);
  if (diffSec < 0) return "just now";
  if (diffSec < 60) return `${diffSec}s ago`;
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  return `${Math.floor(diffSec / 86400)}d ago`;
};

export const formatTimestamp = (dateStr) => {
  if (!dateStr) return "--:--:--";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return String(dateStr);
    return d.toISOString().replace("T", " ").substring(0, 19);
  } catch {
    return String(dateStr);
  }
};

export const getRegimeBadge = (regime) => {
  const r = (regime || "NEUTRAL").toUpperCase();
  if (r.includes("BULL") || r.includes("TREND")) return { label: r.replace(/_/g, " "), color: "badge-green" };
  if (r.includes("BEAR")) return { label: r.replace(/_/g, " "), color: "badge-red" };
  if (r.includes("VOLATIL")) return { label: r.replace(/_/g, " "), color: "badge-yellow" };
  return { label: r.replace(/_/g, " "), color: "badge-cyan" };
};
