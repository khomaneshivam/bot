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
  const isCrypto = symbol.includes("USDT") || symbol.includes("BTC") || symbol.includes("ETH");
  if (isCrypto && num > 100) {
    return `$${num.toFixed(2)}`;
  }
  return `$${num.toFixed(4)}`;
};

export const formatPnL = (val) => {
  const num = Number(val) || 0;
  const sign = num > 0 ? "+" : (num < 0 ? "-" : "");
  return `${sign}$${Math.abs(num).toFixed(2)}`;
};

export const formatPercent = (val) => {
  const num = Number(val) || 0;
  const sign = num > 0 ? "+" : "";
  return `${sign}${num.toFixed(2)}%`;
};

export const getPnLColorClass = (val) => {
  const num = Number(val) || 0;
  if (num > 0) return "text-green";
  if (num < 0) return "text-red";
  return "text-muted";
};

export const getRegimeBadge = (regime) => {
  const r = (regime || "NEUTRAL").toUpperCase();
  if (r.includes("BULL")) return { label: r.replace(/_/g, " "), color: "badge-green" };
  if (r.includes("BEAR")) return { label: r.replace(/_/g, " "), color: "badge-red" };
  if (r.includes("VOLATIL")) return { label: r.replace(/_/g, " "), color: "badge-yellow" };
  return { label: r.replace(/_/g, " "), color: "badge-cyan" };
};
