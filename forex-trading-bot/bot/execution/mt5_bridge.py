import os
import time
from typing import Dict, Optional, Tuple
from bot.config.settings import settings

# Attempt MetaTrader5 import safely
try:
    import MetaTrader5 as mt5
    MT5_INSTALLED = True
except ImportError:
    mt5 = None
    MT5_INSTALLED = False

class MT5Bridge:
    """
    Institutional Bridge between Python Trading Engine and MetaTrader 5 Terminal.
    Handles authentication, live account balance sync, symbol resolution, and order routing.
    """
    def __init__(self):
        self.is_connected = False
        self.account_id = settings.MT5_ACCOUNT
        self.password = settings.MT5_PASSWORD
        self.server = settings.MT5_SERVER
        self.magic_number = settings.MT5_MAGIC_NUMBER
        self.last_error = ""

    def connect(self) -> bool:
        """Initializes and logs into the MetaTrader 5 terminal."""
        if not MT5_INSTALLED:
            self.last_error = "MetaTrader5 Python package not available"
            return False

        try:
            # Step 1: Initialize terminal connection
            if not mt5.initialize():
                err = mt5.last_error()
                self.last_error = f"MT5 initialize failed: {err}. Ensure MT5 desktop terminal is open."
                return False

            # Step 2: Attempt login if credentials are provided
            if self.account_id and self.password and self.server and self.server != "*wRlP5Ja":
                authorized = mt5.login(
                    login=self.account_id,
                    password=self.password,
                    server=self.server
                )
                if not authorized:
                    err = mt5.last_error()
                    self.last_error = f"MT5 login failed for account {self.account_id} on server '{self.server}': {err}"
                    print(f"[MT5Bridge] ⚠️ {self.last_error}")
                    return False
            
            # Step 3: Verify terminal information
            terminal_info = mt5.terminal_info()
            account_info = mt5.account_info()
            
            if account_info is not None:
                self.is_connected = True
                print(f"[MT5Bridge] ✅ Connected to MT5 Account #{account_info.login} ({account_info.company}) | Balance: ${account_info.balance:.2f} | Leverage: 1:{account_info.leverage}")
                return True
            else:
                self.is_connected = True
                print("[MT5Bridge] ✅ MT5 Terminal initialized (Demo mode ready)")
                return True

        except Exception as e:
            self.last_error = str(e)
            print(f"[MT5Bridge] Connection error: {e}")
            return False

    def get_live_account_info(self) -> Dict:
        """Fetches live balance, equity, and margin from the MT5 broker account."""
        if not self.is_connected and not self.connect():
            return {"balance": 0.0, "equity": 0.0, "margin": 0.0, "connected": False, "error": self.last_error}

        try:
            acc = mt5.account_info()
            if acc:
                return {
                    "balance": round(acc.balance, 2),
                    "equity": round(acc.equity, 2),
                    "margin": round(acc.margin, 2),
                    "free_margin": round(acc.margin_free, 2),
                    "currency": acc.currency,
                    "connected": True,
                    "server": acc.server
                }
        except Exception as e:
            self.last_error = str(e)

        return {"balance": 0.0, "equity": 0.0, "connected": False, "error": self.last_error}

    def resolve_broker_symbol(self, standard_symbol: str) -> Optional[str]:
        """
        Maps standard symbols (e.g. 'EURUSD') to broker-specific symbols
        (e.g. 'EURUSD', 'EURUSDm', 'EURUSD.pro', 'EURUSD.r').
        """
        if not self.is_connected and not self.connect():
            return None

        clean = standard_symbol.upper().replace("/", "").replace("-", "")
        candidates = [clean, f"{clean}m", f"{clean}.pro", f"{clean}.r", f"{clean}_i", f"{clean}micro"]

        for cand in candidates:
            info = mt5.symbol_info(cand)
            if info is not None:
                if not info.visible:
                    mt5.symbol_select(cand, True)
                return cand

        return None

    def send_order(
        self,
        symbol: str,
        direction: str,
        volume: float,
        sl: float,
        tp: float,
        comment: str = "QuantBot"
    ) -> Tuple[bool, Optional[int], Optional[float], str]:
        """
        Sends a live or demo market order to MetaTrader 5 with strict slippage and safety controls.
        
        Returns: (success: bool, order_ticket: int, fill_price: float, error_message: str)
        """
        if not self.is_connected and not self.connect():
            return False, None, None, f"MT5 not connected: {self.last_error}"

        broker_symbol = self.resolve_broker_symbol(symbol)
        if not broker_symbol:
            return False, None, None, f"Symbol '{symbol}' not recognized by MT5 broker"

        tick = mt5.symbol_info_tick(broker_symbol)
        if not tick:
            return False, None, None, f"Failed to get live tick for {broker_symbol}"

        order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
        price = tick.ask if direction == "BUY" else tick.bid

        # Check broker spread safety (Spread Filter)
        symbol_info = mt5.symbol_info(broker_symbol)
        if symbol_info and symbol_info.spread > 40:  # More than 4 pips spread
            return False, None, None, f"VETO: Broker spread too wide ({symbol_info.spread} points)"

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": broker_symbol,
            "volume": float(volume),
            "type": order_type,
            "price": price,
            "sl": float(sl),
            "tp": float(tp),
            "deviation": 20,
            "magic": self.magic_number,
            "comment": comment[:31],
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # Send order to MT5 terminal
        result = mt5.order_send(request)
        if result is None:
            err = mt5.last_error()
            return False, None, None, f"MT5 order_send returned None. Error: {err}"

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return False, None, None, f"MT5 order failed. Retcode {result.retcode}: {result.comment}"

        fill_price = result.price if result.price > 0 else price
        print(f"[MT5Bridge] 🎯 Order executed on MT5 #{result.order} | {direction} {volume} {broker_symbol} @ {fill_price}")
        return True, result.order, fill_price, "Executed successfully"

    def close_mt5_position(self, ticket: int) -> Tuple[bool, str]:
        """Closes an open position on MT5 by ticket ID."""
        if not self.is_connected and not self.connect():
            return False, "MT5 not connected"

        pos = mt5.positions_get(ticket=ticket)
        if not pos or len(pos) == 0:
            return False, f"Position #{ticket} not found on MT5"

        position = pos[0]
        broker_symbol = position.symbol
        tick = mt5.symbol_info_tick(broker_symbol)
        if not tick:
            return False, "Failed to retrieve tick for position close"

        close_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = tick.bid if position.type == mt5.ORDER_TYPE_BUY else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": broker_symbol,
            "volume": position.volume,
            "type": close_type,
            "price": price,
            "deviation": 20,
            "magic": self.magic_number,
            "comment": "QuantBot Close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            return True, "Closed on MT5"
        else:
            err = result.comment if result else str(mt5.last_error())
            return False, f"MT5 close error: {err}"

    def shutdown(self):
        """Disconnects cleanly from MT5."""
        if MT5_INSTALLED and self.is_connected:
            try:
                mt5.shutdown()
                self.is_connected = False
            except Exception:
                pass

mt5_bridge = MT5Bridge()
