try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False
import pandas as pd

TIMEFRAME_MAP = {
    "M1": getattr(mt5, "TIMEFRAME_M1", 1),
    "M5": getattr(mt5, "TIMEFRAME_M5", 5),
    "M15": getattr(mt5, "TIMEFRAME_M15", 15),
    "H1": getattr(mt5, "TIMEFRAME_H1", 16385),
}

def init_mt5():
    if not mt5.initialize():
        raise RuntimeError("MT5 initialize() failed")

def shutdown_mt5():
    mt5.shutdown()

def get_rates(symbol, timeframe_str, bars):
    timeframe = TIMEFRAME_MAP[timeframe_str]
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
    if rates is None:
        raise RuntimeError("Failed to fetch rates")
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return df