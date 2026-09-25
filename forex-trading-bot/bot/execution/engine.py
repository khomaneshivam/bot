import time
import uuid
import numpy as np
from typing import Dict, List, Optional, Tuple
from bot.config.settings import settings
from bot.risk.risk_manager import risk_manager
from bot.ai.ml_engine import ml_engine
from bot.ai.correlation_engine import correlation_engine
from bot.strategies.ensemble import strategy_ensemble
from bot.execution.trade_ledger import trade_ledger
from bot.execution.mt5_bridge import mt5_bridge
from bot.risk.psychology_guard import psychology_guard

def calculate_trade_pnl(symbol: str, direction: str, entry_price: float, current_price: float, size: float) -> Tuple[float, float]:
    """
    Calculates exact institutional PnL in USD:
    - Forex currency pairs: 1 standard lot = 100,000 units. 0.01 micro-lot = 1,000 units ($0.10/pip).
    - Gold (XAUUSD): 1 lot = 100 oz.
    - Crypto (BTC/ETH/SOL): size in units of coin.
    """
    clean_sym = symbol.upper().replace("-", "").replace("/", "")
    is_crypto = "USDT" in clean_sym
    is_gold = "XAU" in clean_sym

    price_diff = (current_price - entry_price) if direction == "BUY" else (entry_price - current_price)

    if is_crypto:
        pnl = price_diff * size
    elif is_gold:
        units = size * 100.0
        pnl = price_diff * units
    else:
        # Standard Forex Currency Pairs (1 lot = 100,000 units)
        units = size * 100000.0
        if clean_sym.startswith("USD"):
            pnl = (price_diff / max(current_price, 1e-4)) * units
        else:
            pnl = price_diff * units

    pnl = round(pnl, 2)
    entry_notional = max(1.0, entry_price * (size if is_crypto else (size * 100.0 if is_gold else size * 100000.0)))
    return_pct = round((pnl / entry_notional) * 100.0, 2)
    return pnl, return_pct

class ExecutionEngine:
    def __init__(self):
        self.mode = settings.MODE  # "paper", "demo", "live"
        
        # Portfolio
        self.paper_balance = settings.PAPER_STARTING_BALANCE
        self.paper_equity = settings.PAPER_STARTING_BALANCE
        self.paper_realized_pnl = 0.0
        self.open_positions: List[Dict] = []
        self.closed_trades: List[Dict] = []
        
        # Load historical trades from SQLite ledger on boot
        self._load_ledger_history()

    def _load_ledger_history(self):
        try:
            self.closed_trades = trade_ledger.get_recent_trades(limit=50)
            summary = trade_ledger.get_audit_summary()
            self.winning_trades_count = summary["wins"]
            self.losing_trades_count = summary["losses"]
            self.paper_realized_pnl = summary["net_pnl"]
            self.paper_balance = settings.PAPER_STARTING_BALANCE + self.paper_realized_pnl
            self.paper_equity = self.paper_balance
        except Exception as e:
            print(f"[ExecutionEngine] Ledger boot note: {e}")
            self.winning_trades_count = 0
            self.losing_trades_count = 0

    def reset_capital(self, starting_balance: float = 100.0):
        """Resets the engine and ledger to a clean starting capital (e.g. $100.00)."""
        self.paper_balance = starting_balance
        self.paper_equity = starting_balance
        self.paper_realized_pnl = 0.0
        self.open_positions = []
        self.closed_trades = []
        self.winning_trades_count = 0
        self.losing_trades_count = 0
        trade_ledger.reset_ledger()
        risk_manager.reset_daily_baseline(starting_balance)
        print(f"[ExecutionEngine] 💰 Capital initialized to ${starting_balance:.2f} in {self.mode.upper()} mode.")

    def set_mode(self, new_mode: str) -> str:
        if new_mode in ["paper", "demo", "live"]:
            self.mode = new_mode
            settings.MODE = new_mode
            trade_ledger.log_risk_event("MODE_SWITCH", "SYSTEM", f"Switched operating mode to {new_mode.upper()}")
            print(f"[ExecutionEngine] ⚠️ Switched operating mode to: {new_mode.upper()}")
            return self.mode
        return self.mode

    def get_account_summary(self) -> Dict:
        """Returns unified portfolio balance, equity, and ledger statistics."""
        unrealized = sum(p.get("unrealized_pnl", 0.0) for p in self.open_positions)
        equity = self.paper_balance + unrealized
        self.paper_equity = equity
        risk_manager.update_equity(equity)

        summary = trade_ledger.get_audit_summary()
        total_trades = summary["total_trades"]
        win_rate = summary["win_rate"]
        profit_factor = summary["profit_factor"]

        # If in Demo or Live mode and MT5 is connected, report live broker account stats
        if self.mode in ["demo", "live"]:
            mt5_info = mt5_bridge.get_live_account_info()
            if mt5_info.get("connected"):
                return {
                    "mode": self.mode,
                    "balance": mt5_info["balance"],
                    "equity": mt5_info["equity"],
                    "unrealized_pnl": round(mt5_info["equity"] - mt5_info["balance"], 2),
                    "realized_pnl": round(self.paper_realized_pnl, 2),
                    "win_rate": win_rate,
                    "total_trades": total_trades,
                    "winning_trades": summary["wins"],
                    "losing_trades": summary["losses"],
                    "profit_factor": profit_factor,
                    "open_positions_count": len(self.open_positions),
                    "daily_drawdown_limit_hit": risk_manager.daily_drawdown_limit_hit,
                    "risk_vetoes_count": summary["risk_vetoes_count"],
                    "broker_server": mt5_info.get("server", "MT5")
                }

        return {
            "mode": self.mode,
            "balance": round(self.paper_balance, 2),
            "equity": round(equity, 2),
            "unrealized_pnl": round(unrealized, 2),
            "realized_pnl": round(self.paper_realized_pnl, 2),
            "win_rate": win_rate,
            "total_trades": total_trades,
            "winning_trades": summary["wins"],
            "losing_trades": summary["losses"],
            "profit_factor": profit_factor,
            "open_positions_count": len(self.open_positions),
            "daily_drawdown_limit_hit": risk_manager.daily_drawdown_limit_hit,
            "risk_vetoes_count": summary["risk_vetoes_count"]
        }

    def place_order(
        self,
        symbol: str,
        direction: str,
        size: float,
        entry_price: float,
        sl: float,
        tp: float,
        strategy_name: str,
        reason: str,
        features_snapshot: Optional[np.ndarray] = None,
        market_regime: str = "UNKNOWN",
        confidence: float = 0.5
    ) -> Optional[Dict]:
        """
        Executes a new market order after institutional risk & correlation screening.
        """
        # 1. Circuit breaker: Daily Drawdown Guard
        if risk_manager.daily_drawdown_limit_hit:
            msg = "Order rejected: Max Daily Drawdown threshold breached. Circuit breaker active."
            trade_ledger.log_risk_event("CIRCUIT_BREAKER_VETO", symbol, msg)
            print(f"[ExecutionEngine] 🛑 {msg}")
            return None

        # 2. Maximum open positions limit
        if len(self.open_positions) >= settings.MAX_OPEN_POSITIONS:
            msg = f"Order rejected: Max open positions ({settings.MAX_OPEN_POSITIONS}) reached."
            trade_ledger.log_risk_event("MAX_POSITIONS_VETO", symbol, msg)
            return None

        # 3. Check for existing position on the exact same symbol
        for pos in self.open_positions:
            if pos["symbol"] == symbol:
                return None

        # 4. CRITICAL REAL-MONEY SAFETY: Cross-Asset Correlation Risk Filter
        is_vetoed, corr_reason = correlation_engine.evaluate_correlation_guard(
            candidate_symbol=symbol,
            candidate_direction=direction,
            existing_positions=self.open_positions
        )
        if is_vetoed:
            trade_ledger.log_risk_event("CORRELATION_VETO", symbol, corr_reason)
            print(f"[ExecutionEngine] 🛡️ {corr_reason}")
            return None

        trade_id = str(uuid.uuid4())[:8]

        # Apply slippage simulation for paper trading
        fill_price = entry_price
        if self.mode == "paper":
            slippage = entry_price * 0.0001
            fill_price = entry_price + slippage if direction == "BUY" else entry_price - slippage

        dxy_val = correlation_engine.calculate_dxy_proxy()

        position = {
            "id": trade_id,
            "symbol": symbol,
            "direction": direction,
            "size": size,
            "entry_price": round(fill_price, 4),
            "current_price": round(fill_price, 4),
            "sl": round(sl, 4),
            "tp": round(tp, 4),
            "unrealized_pnl": 0.0,
            "open_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "strategy": strategy_name,
            "reason": reason,
            "regime": market_regime,
            "dxy_at_entry": dxy_val,
            "features_at_entry": features_snapshot.tolist() if features_snapshot is not None else []
        }

        # Handle Live Broker / Exchange execution if demo or live mode
        mt5_ticket = None
        if self.mode in ["demo", "live"]:
            is_crypto = "USDT" in symbol.upper()
            if not is_crypto:
                lot_size = settings.DEFAULT_LOT_FOREX if self.mode == "demo" else min(0.02, settings.DEFAULT_LOT_FOREX)
                ok, ticket, mt5_fill, err = mt5_bridge.send_order(
                    symbol=symbol,
                    direction=direction,
                    volume=lot_size,
                    sl=sl,
                    tp=tp,
                    comment=f"QuantBot-{self.mode.upper()}"
                )
                if ok and ticket:
                    mt5_ticket = ticket
                    fill_price = mt5_fill
                    position["mt5_ticket"] = ticket
                    position["entry_price"] = round(mt5_fill, 4)
                    print(f"[ExecutionEngine] 🏛️ MT5 Order Confirmed Ticket #{ticket} @ {mt5_fill}")
                else:
                    print(f"[ExecutionEngine] ⚠️ MT5 Route ({self.mode}): {err}. Operating in simulated tracking.")

        self.open_positions.append(position)

        # Log into persistent SQLite ledger
        trade_ledger.log_trade_opened(
            trade_id=trade_id,
            symbol=symbol,
            direction=direction,
            size=size,
            entry_price=round(fill_price, 4),
            sl=round(sl, 4),
            tp=round(tp, 4),
            strategy=strategy_name,
            regime=market_regime,
            confidence=confidence,
            dxy_val=dxy_val,
            features=position["features_at_entry"]
        )

        print(f"[ExecutionEngine] 🚀 [{self.mode.upper()}] Opened {direction} on {symbol} @ {fill_price:.4f} | Size: {size} | SL: {sl:.4f} | TP: {tp:.4f}")
        return position

    def update_positions_and_check_exits(self, current_ticks: Dict[str, dict]):
        """
        Evaluates active positions with incoming ticks.
        Checks Stop-Loss, Take-Profit, and Trailing Stops.
        """
        closed_in_this_cycle = []

        for pos in list(self.open_positions):
            symbol = pos["symbol"]
            tick = current_ticks.get(symbol)
            if not tick:
                continue

            current_price = float(tick["price"])
            pos["current_price"] = round(current_price, 4)

            # Calculate floating PnL & return %
            pnl, ret_pct = calculate_trade_pnl(symbol, pos["direction"], pos["entry_price"], current_price, pos["size"])
            pos["unrealized_pnl"] = pnl
            pos["return_pct"] = ret_pct

            # Dynamic ATR Trailing Stop
            atr_est = abs(pos["entry_price"] - pos["sl"]) / max(settings.STOP_LOSS_ATR_MULT, 1.0)
            new_sl = risk_manager.evaluate_trailing_stop(
                pos["direction"],
                pos["entry_price"],
                current_price,
                pos["sl"],
                atr_est
            )
            if new_sl:
                pos["sl"] = new_sl

            # Check SL / TP
            sl_hit = False
            if pos["direction"] == "BUY" and current_price <= pos["sl"]:
                sl_hit = True
            elif pos["direction"] == "SELL" and current_price >= pos["sl"]:
                sl_hit = True

            tp_hit = False
            if pos["direction"] == "BUY" and current_price >= pos["tp"]:
                tp_hit = True
            elif pos["direction"] == "SELL" and current_price <= pos["tp"]:
                tp_hit = True

            if sl_hit:
                self.close_position(pos["id"], exit_reason="STOP_LOSS", exit_price=pos["sl"])
                closed_in_this_cycle.append(pos["id"])
            elif tp_hit:
                self.close_position(pos["id"], exit_reason="TAKE_PROFIT", exit_price=pos["tp"])
                closed_in_this_cycle.append(pos["id"])

        return closed_in_this_cycle

    def close_position(self, position_id: str, exit_reason: str = "MANUAL", exit_price: Optional[float] = None) -> Optional[Dict]:
        """Closes a position, updates PnL, and triggers the Mistake Retraining loop if loss occurred."""
        for i, pos in enumerate(self.open_positions):
            if pos["id"] == position_id:
                close_price = exit_price if exit_price is not None else pos["current_price"]
                pnl, ret_pct = calculate_trade_pnl(pos["symbol"], pos["direction"], pos["entry_price"], close_price, pos["size"])

                pos["close_price"] = round(close_price, 4)
                pos["close_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
                pos["pnl"] = pnl
                pos["return_pct"] = ret_pct
                pos["exit_reason"] = exit_reason

                # STRICT ACCOUNT BALANCE UPDATE: Deduct loss or add profit to cash balance
                self.paper_balance = round(self.paper_balance + pnl, 2)
                self.paper_realized_pnl = round(self.paper_realized_pnl + pnl, 2)

                loss_cause = None

                if pnl >= 0:
                    self.winning_trades_count += 1
                    strategy_ensemble.reward_strategy_win(pos["strategy"], pnl)
                    print(f"[ExecutionEngine] 🟢 WIN Trade #{pos['id']}: Closed at +${pnl:.2f} profit ({exit_reason})")
                else:
                    self.losing_trades_count += 1
                    strategy_ensemble.penalize_strategy_loss(pos["strategy"])
                    print(f"[ExecutionEngine] 🔴 WRONG Trade #{pos['id']}: Closed at -${abs(pnl):.2f} loss ({exit_reason})")

                    # CRITICAL REQUIREMENT: Trigger Retraining on Wrong Trades!
                    if len(pos.get("features_at_entry", [])) > 0:
                        feat_arr = np.array(pos["features_at_entry"], dtype=np.float32)
                        ml_engine.log_wrong_trade(
                            trade_id=pos["id"],
                            symbol=pos["symbol"],
                            direction=pos["direction"],
                            entry_price=pos["entry_price"],
                            exit_price=close_price,
                            pnl=pnl,
                            features_at_entry=feat_arr,
                            market_regime=pos.get("regime", "UNKNOWN"),
                            strategy_used=pos.get("strategy", "UNKNOWN")
                        )
                        loss_cause = ml_engine.wrong_trades[-1].get("loss_cause") if ml_engine.wrong_trades else None

                # Update SQLite Trade Ledger
                trade_ledger.log_trade_closed(
                    trade_id=pos["id"],
                    close_price=round(close_price, 4),
                    pnl=pnl,
                    exit_reason=exit_reason,
                    loss_cause=loss_cause
                )

                # Update 20+ Year Trader Psychology State (Tilt, Discipline, Drawdown)
                psychology_guard.on_trade_closed(pnl, pos["symbol"], self.paper_balance)

                # Close on MT5 if ticket was issued
                if pos.get("mt5_ticket"):
                    ok, close_msg = mt5_bridge.close_mt5_position(pos["mt5_ticket"])
                    print(f"[ExecutionEngine] MT5 Position #{pos['mt5_ticket']} close status: {close_msg}")

                record = self.open_positions.pop(i)
                self.closed_trades.insert(0, record)
                return record

        return None

    def close_all_positions(self, reason: str = "EMERGENCY_STOP") -> int:
        """Emergency kill switch: liquidates all open positions instantly."""
        count = len(self.open_positions)
        trade_ledger.log_risk_event("KILL_SWITCH", "ALL", f"Emergency kill switch triggered: {count} positions liquidated")
        while len(self.open_positions) > 0:
            self.close_position(self.open_positions[0]["id"], exit_reason=reason)
        print(f"[ExecutionEngine] 🛑 Emergency stop executed: Closed {count} positions.")
        return count

execution_engine = ExecutionEngine()
