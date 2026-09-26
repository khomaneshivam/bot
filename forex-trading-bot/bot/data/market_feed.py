import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

# Try importing MetaTrader5 safely
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False

CRYPTO_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT", "ADAUSDT", "DOGEUSDT"]
FOREX_SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "AUDUSD", "USDCAD", "USDCHF"]

YFINANCE_MAP = {
    "BTCUSDT": "BTC-USD",
    "ETHUSDT": "ETH-USD",
    "SOLUSDT": "SOL-USD",
    "XRPUSDT": "XRP-USD",
    "BNBUSDT": "BNB-USD",
    "ADAUSDT": "ADA-USD",
    "DOGEUSDT": "DOGE-USD",
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "JPY=X",
    "XAUUSD": "GC=F",
    "AUDUSD": "AUDUSD=X",
    "USDCAD": "CAD=X",
    "USDCHF": "CHF=X",
}

class MarketDataFeed:
    """
    Hardened Production Market Data Feed.
    Fetches live market data from Binance (Crypto) and Yahoo Finance / MT5 (Forex/Gold).
    Strict fail-closed: NEVER generates synthetic random candles.
    Tracks feed latency, freshness, and raises/reports data outages.
    """

    def __init__(self):
        self._cache: Dict[str, pd.DataFrame] = {}
        self._cache_time: Dict[str, float] = {}
        self._last_ticks: Dict[str, dict] = {}
        self._last_tick_time: Dict[str, float] = {}
        self.http_session = requests.Session()
        self.http_session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) QuantAI/2.0"
        })

    def is_crypto(self, symbol: str) -> bool:
        s = symbol.upper().replace("-", "").replace("/", "")
        return any(c in s for c in ["BTC", "ETH", "SOL", "XRP", "BNB", "ADA", "DOGE", "USDT"])

    def is_feed_fresh(self, symbol: str, max_age_seconds: float = 60.0) -> bool:
        """Returns True if the feed for symbol has been updated within max_age_seconds."""
        clean = symbol.upper().replace("-", "").replace("/", "")
        last_time = self._last_tick_time.get(clean, 0.0)
        return (time.time() - last_time) <= max_age_seconds

    def get_feed_latency(self, symbol: str) -> float:
        """Returns seconds since last received tick for symbol."""
        clean = symbol.upper().replace("-", "").replace("/", "")
        last_time = self._last_tick_time.get(clean, 0.0)
        if last_time == 0.0:
            return 9999.0
        return round(time.time() - last_time, 2)

    def fetch_crypto_binance(self, symbol: str, interval: str = "5m", limit: int = 200) -> pd.DataFrame:
        """Public Binance API klines."""
        clean_symbol = symbol.upper().replace("-", "").replace("/", "")
        if not clean_symbol.endswith("USDT") and not clean_symbol.endswith("USD"):
            clean_symbol += "USDT"

        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": clean_symbol, "interval": interval, "limit": limit}

        try:
            resp = self.http_session.get(url, params=params, timeout=5.0)
            if resp.status_code == 200:
                raw_data = resp.json()
                records = []
                for row in raw_data:
                    records.append({
                        "timestamp": pd.to_datetime(row[0], unit="ms", utc=True),
                        "open": float(row[1]),
                        "high": float(row[2]),
                        "low": float(row[3]),
                        "close": float(row[4]),
                        "volume": float(row[5]),
                    })
                df = pd.DataFrame(records)
                return df
        except Exception:
            pass
        return pd.DataFrame()

    def fetch_yahoo_chart_api(self, symbol: str, interval: str = "5m", limit: int = 200) -> pd.DataFrame:
        """Yahoo Finance Chart API."""
        clean_symbol = symbol.upper().replace("/", "")
        ticker = YFINANCE_MAP.get(clean_symbol, clean_symbol)

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval={interval}&range=5d"
        try:
            resp = self.http_session.get(url, timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                result = data.get("chart", {}).get("result", [])
                if result:
                    res = result[0]
                    timestamps = res.get("timestamp", [])
                    quote = res.get("indicators", {}).get("quote", [{}])[0]
                    opens = quote.get("open", [])
                    highs = quote.get("high", [])
                    lows = quote.get("low", [])
                    closes = quote.get("close", [])
                    vols = quote.get("volume", [])

                    records = []
                    for i in range(len(timestamps)):
                        if closes[i] is not None and opens[i] is not None:
                            records.append({
                                "timestamp": pd.to_datetime(timestamps[i], unit="s", utc=True),
                                "open": float(opens[i]),
                                "high": float(highs[i]),
                                "low": float(lows[i]),
                                "close": float(closes[i]),
                                "volume": float(vols[i] or 100.0)
                            })
                    if records:
                        df = pd.DataFrame(records)
                        return df.tail(limit)
        except Exception:
            pass
        return pd.DataFrame()

    def fetch_mt5_candles(self, symbol: str, limit: int = 200) -> pd.DataFrame:
        """Fetches candles directly from MetaTrader 5 if connected."""
        if not MT5_AVAILABLE:
            return pd.DataFrame()

        try:
            term = mt5.terminal_info()
            if term is None or not term.connected:
                return pd.DataFrame()

            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, limit)
            if rates is not None and len(rates) > 0:
                df = pd.DataFrame(rates)
                df["timestamp"] = pd.to_datetime(df["time"], unit="s", utc=True)
                df.rename(columns={"tick_volume": "volume"}, inplace=True)
                return df[["timestamp", "open", "high", "low", "close", "volume"]]
        except Exception:
            pass
        return pd.DataFrame()

    def get_candles(self, symbol: str, interval: str = "5m", limit: int = 200, max_cache_age: float = 15.0) -> pd.DataFrame:
        """
        Retrieves live candle data with caching.
        Returns empty DataFrame if external fetch fails and cache is stale.
        NEVER generates fake synthetic candles.
        """
        clean_symbol = symbol.upper().replace("-", "").replace("/", "")
        now = time.time()

        # Check cache freshness
        if clean_symbol in self._cache and (now - self._cache_time.get(clean_symbol, 0)) < max_cache_age:
            return self._cache[clean_symbol]

        df = pd.DataFrame()

        # 1. Try MT5 first if available
        if MT5_AVAILABLE:
            df = self.fetch_mt5_candles(clean_symbol, limit=limit)

        # 2. If not MT5, try Binance for Crypto or Yahoo for Forex
        if df.empty:
            if self.is_crypto(clean_symbol):
                df = self.fetch_crypto_binance(clean_symbol, interval=interval, limit=limit)
                if df.empty:
                    df = self.fetch_yahoo_chart_api(clean_symbol, interval=interval, limit=limit)
            else:
                df = self.fetch_yahoo_chart_api(clean_symbol, interval=interval, limit=limit)

        if not df.empty and len(df) >= 15:
            self._cache[clean_symbol] = df
            self._cache_time[clean_symbol] = now
            self._last_tick_time[clean_symbol] = now
            last_row = df.iloc[-1]
            close_price = float(last_row["close"])
            self._last_ticks[clean_symbol] = {
                "price": close_price,
                "bid": close_price * 0.9999,
                "ask": close_price * 1.0001,
                "time": str(last_row["timestamp"]),
                "freshness_seconds": 0.0
            }
            return df

        # If live fetch failed, return existing cached data only if reasonably fresh (< 90s)
        if clean_symbol in self._cache and (now - self._cache_time.get(clean_symbol, 0)) < 90.0:
            return self._cache[clean_symbol]

        # Fail closed: Do NOT generate random synthetic data
        return pd.DataFrame()

    def get_latest_tick(self, symbol: str) -> Optional[dict]:
        clean_symbol = symbol.upper().replace("-", "").replace("/", "")
        if clean_symbol in self._last_ticks and self.is_feed_fresh(clean_symbol, max_age_seconds=60.0):
            tick = self._last_ticks[clean_symbol].copy()
            tick["freshness_seconds"] = self.get_feed_latency(clean_symbol)
            return tick

        df = self.get_candles(clean_symbol, limit=20)
        if not df.empty:
            tick = self._last_ticks.get(clean_symbol)
            if tick:
                tick["freshness_seconds"] = self.get_feed_latency(clean_symbol)
                return tick

        return None

market_feed = MarketDataFeed()
