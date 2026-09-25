try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None
from bot.risk.risk_manager import compute_sl_tp

def has_open_position(symbol):
    if mt5 is None:
        return False
    positions = mt5.positions_get(symbol=symbol)
    return positions is not None and len(positions) > 0

def place_trade(symbol, signal, lot, sl_points, tp_points, magic):
    tick = mt5.symbol_info_tick(symbol)
    info = mt5.symbol_info(symbol)
    if tick is None or info is None:
        print("Symbol info/tick unavailable")
        return None

    point = info.point

    if signal == "BUY":
        price = tick.ask
        order_type = mt5.ORDER_TYPE_BUY
    elif signal == "SELL":
        price = tick.bid
        order_type = mt5.ORDER_TYPE_SELL
    else:
        return None

    sl, tp = compute_sl_tp(price, signal, sl_points, tp_points, point)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": magic,
        "comment": "EMA_RSI_BOT",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    return result