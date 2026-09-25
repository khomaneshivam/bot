try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

def get_open_positions(symbol=None):
    if mt5 is None:
        return []
    positions = mt5.positions_get(symbol=symbol)

    if positions is None:
        return []

    results = []
    for pos in positions:
        results.append({
            "ticket": pos.ticket,
            "symbol": pos.symbol,
            "type": "BUY" if pos.type == 0 else "SELL",
            "volume": pos.volume,
            "price_open": pos.price_open,
            "current_price": pos.price_current,
            "profit": pos.profit
        })

    return results