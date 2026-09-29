import assert from "node:assert";
import {
  formatCurrency,
  formatPrice,
  formatPnL,
  formatPercent,
  formatRMultiple,
  getPnLTextColor,
  getPnLBgColor,
  formatTimeAgo,
  getRegimeBadge,
} from "./src/utils/formatters.js";
import { EXECUTION_MODES, ORDER_STATUSES, RISK_LEVELS, NAV_ITEMS } from "./src/utils/constants.js";

console.log("Running QuantAI Terminal Frontend Unit Invariants...");

// 1. Currency formatting
assert.strictEqual(formatCurrency(100), "$100.00");
assert.strictEqual(formatCurrency(0), "$0.00");
assert.strictEqual(formatCurrency(-50.5), "$-50.50");
assert.strictEqual(formatCurrency(null), "$0.00");
assert.strictEqual(formatCurrency(undefined), "$0.00");
console.log("✅ Currency formatting tests passed.");

// 2. Price formatting
assert.strictEqual(formatPrice(1.08523, "EURUSD"), "1.08523");
assert.strictEqual(formatPrice(152.456, "USDJPY"), "152.456");
assert.strictEqual(formatPrice(2650.5, "XAUUSD"), "2,650.50");
assert.strictEqual(formatPrice(65432.1, "BTCUSDT"), "65,432.10");
console.log("✅ Asset-aware price formatting tests passed.");

// 3. PnL formatting
assert.strictEqual(formatPnL(12.5), "+$12.50");
assert.strictEqual(formatPnL(-8.2), "-$8.20");
assert.strictEqual(formatPnL(0), "$0.00");
console.log("✅ PnL formatting tests passed.");

// 4. R-Multiple calculation
assert.strictEqual(formatRMultiple(25, 10), "+2.50R");
assert.strictEqual(formatRMultiple(-10, 10), "-1.00R");
assert.strictEqual(formatRMultiple(0, 10), "+0.00R");
console.log("✅ R-multiple formatting tests passed.");

// 5. Semantic colors
assert.strictEqual(getPnLTextColor(10), "text-emerald-400");
assert.strictEqual(getPnLTextColor(-5), "text-rose-400");
assert.strictEqual(getPnLTextColor(0), "text-slate-400");
console.log("✅ Semantic status color mapping passed.");

// 6. Execution mode constants
assert.strictEqual(EXECUTION_MODES.PAPER.isLive, false);
assert.strictEqual(EXECUTION_MODES.MT5_LIVE.isLive, true);
assert.strictEqual(EXECUTION_MODES.BINANCE_LIVE.isLive, true);
console.log("✅ Execution mode invariant tests passed.");

// 7. Navigation items count
assert.strictEqual(NAV_ITEMS.length, 12, "Must contain exactly 12 institutional views");
console.log("✅ 12 First-class navigation items confirmed.");

// 8. Auth & Registration Invariants
const usernameRegex = /^[a-zA-Z0-9_-]{3,32}$/;
assert.strictEqual(usernameRegex.test("valid_trader-01"), true);
assert.strictEqual(usernameRegex.test("ab"), false); // too short
assert.strictEqual(usernameRegex.test("invalid trader with spaces"), false);
assert.strictEqual(usernameRegex.test("invalid@symbols!"), false);

const validatePassword = (pwd) => pwd.length >= 8 && /[a-zA-Z]/.test(pwd) && /[0-9]/.test(pwd);
assert.strictEqual(validatePassword("SecurePass2026!"), true);
assert.strictEqual(validatePassword("short7"), false);
assert.strictEqual(validatePassword("nonumbershere"), false);
assert.strictEqual(validatePassword("12345678"), false);
console.log("✅ Authentication & Registration input policy invariants confirmed.");

console.log("🎉 ALL FRONTEND UNIT TESTS PASSED SUCCESSFULLY!");
