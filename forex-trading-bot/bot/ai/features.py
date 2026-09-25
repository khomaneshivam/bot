import pandas as pd
import numpy as np
import ta

FEATURE_COLUMNS = [
    # Returns & Momentum
    "ret_1", "ret_3", "ret_5", "ret_10", "ret_20",
    "rsi_14", "rsi_7", "rsi_21", "rsi_slope",
    "stoch_k", "stoch_d", "stoch_diff",
    "williams_r", "cci_20", "roc_10",
    
    # Trend & Moving Averages
    "dist_ema_9", "dist_ema_21", "dist_ema_50", "dist_ema_200",
    "ema_spread_fast", "ema_spread_mid", "ema_spread_slow",
    "macd_norm", "macd_diff_norm", "macd_signal_norm",
    "adx", "adx_pos", "adx_neg", "adx_diff",
    
    # Volatility & Bands
    "atr_pct", "atr_ratio",
    "bb_pct_b", "bb_bandwidth", "bb_dist_upper", "bb_dist_lower",
    "kc_pct", "donchian_pct", "high_low_spread",
    
    # Volume & Flow
    "vol_ratio", "mfi_14", "obv_slope", "vwap_dist",
    
    # Price Action & Candlestick Metrics
    "candle_body_ratio", "upper_shadow_ratio", "lower_shadow_ratio",
    "is_bull_candle", "consecutive_bars",
    
    # Market Regime Dimensions
    "regime_trend_score", "regime_volatility_score", "regime_chop_score"
]

def compute_all_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes 60+ quantitative trading features and market regime indicators
    on an OHLCV dataframe.
    """
    if df is None or len(df) < 30:
        return df

    data = df.copy()
    close = data["close"]
    high = data["high"]
    low = data["low"]
    open_ = data["open"]
    volume = data["volume"]

    # 1. Returns & Momentum
    data["ret_1"] = close.pct_change(1)
    data["ret_3"] = close.pct_change(3)
    data["ret_5"] = close.pct_change(5)
    data["ret_10"] = close.pct_change(10)
    data["ret_20"] = close.pct_change(20)

    data["rsi_14"] = ta.momentum.rsi(close, window=14)
    data["rsi_7"] = ta.momentum.rsi(close, window=7)
    data["rsi_21"] = ta.momentum.rsi(close, window=21)
    data["rsi_slope"] = data["rsi_14"].diff(3)

    stoch = ta.momentum.StochasticOscillator(high=high, low=low, close=close, window=14, smooth_window=3)
    data["stoch_k"] = stoch.stoch()
    data["stoch_d"] = stoch.stoch_signal()
    data["stoch_diff"] = data["stoch_k"] - data["stoch_d"]

    data["williams_r"] = ta.momentum.williams_r(high, low, close, lbp=14)
    data["cci_20"] = ta.trend.cci(high, low, close, window=20)
    data["roc_10"] = ta.momentum.roc(close, window=10)

    # 2. Trend & Moving Averages
    ema_9 = ta.trend.ema_indicator(close, window=9)
    ema_21 = ta.trend.ema_indicator(close, window=21)
    ema_50 = ta.trend.ema_indicator(close, window=50)
    ema_200 = ta.trend.ema_indicator(close, window=200 if len(close) >= 200 else len(close)//2)

    data["ema_9"] = ema_9
    data["ema_21"] = ema_21
    data["ema_50"] = ema_50
    data["ema_200"] = ema_200

    data["dist_ema_9"] = (close - ema_9) / (close + 1e-8)
    data["dist_ema_21"] = (close - ema_21) / (close + 1e-8)
    data["dist_ema_50"] = (close - ema_50) / (close + 1e-8)
    data["dist_ema_200"] = (close - ema_200) / (close + 1e-8)

    data["ema_spread_fast"] = (ema_9 - ema_21) / (close + 1e-8)
    data["ema_spread_mid"] = (ema_21 - ema_50) / (close + 1e-8)
    data["ema_spread_slow"] = (ema_50 - ema_200) / (close + 1e-8)

    macd_ind = ta.trend.MACD(close)
    data["macd"] = macd_ind.macd()
    data["macd_signal"] = macd_ind.macd_signal()
    data["macd_diff"] = macd_ind.macd_diff()
    data["macd_norm"] = data["macd"] / (close + 1e-8)
    data["macd_signal_norm"] = data["macd_signal"] / (close + 1e-8)
    data["macd_diff_norm"] = data["macd_diff"] / (close + 1e-8)

    adx_ind = ta.trend.ADXIndicator(high=high, low=low, close=close, window=14)
    data["adx"] = adx_ind.adx()
    data["adx_pos"] = adx_ind.adx_pos()
    data["adx_neg"] = adx_ind.adx_neg()
    data["adx_diff"] = data["adx_pos"] - data["adx_neg"]

    # 3. Volatility & Bands
    atr_ind = ta.volatility.AverageTrueRange(high=high, low=low, close=close, window=14)
    data["atr_14"] = atr_ind.average_true_range()
    data["atr_pct"] = data["atr_14"] / (close + 1e-8)
    data["atr_ratio"] = data["atr_14"] / (data["atr_14"].rolling(50).mean() + 1e-8)

    bb_ind = ta.volatility.BollingerBands(close=close, window=20, window_dev=2)
    data["bb_high"] = bb_ind.bollinger_hband()
    data["bb_mid"] = bb_ind.bollinger_mavg()
    data["bb_low"] = bb_ind.bollinger_lband()
    data["bb_pct_b"] = bb_ind.bollinger_pband()
    data["bb_bandwidth"] = bb_ind.bollinger_wband()
    data["bb_dist_upper"] = (data["bb_high"] - close) / (close + 1e-8)
    data["bb_dist_lower"] = (close - data["bb_low"]) / (close + 1e-8)

    kc_ind = ta.volatility.KeltnerChannel(high=high, low=low, close=close, window=20)
    data["kc_high"] = kc_ind.keltner_channel_hband()
    data["kc_low"] = kc_ind.keltner_channel_lband()
    data["kc_pct"] = (close - data["kc_low"]) / (data["kc_high"] - data["kc_low"] + 1e-8)

    donchian_high = high.rolling(20).max()
    donchian_low = low.rolling(20).min()
    data["donchian_high"] = donchian_high
    data["donchian_low"] = donchian_low
    data["donchian_pct"] = (close - donchian_low) / (donchian_high - donchian_low + 1e-8)
    data["high_low_spread"] = (high - low) / (close + 1e-8)

    # 4. Volume & Flow
    vol_sma_20 = volume.rolling(20).mean()
    data["vol_ratio"] = volume / (vol_sma_20 + 1e-8)
    data["mfi_14"] = ta.volume.money_flow_index(high, low, close, volume, window=14)
    obv = ta.volume.on_balance_volume(close, volume)
    data["obv_slope"] = obv.pct_change(5)

    typical_price = (high + low + close) / 3
    vwap_approx = (typical_price * volume).rolling(20).sum() / (volume.rolling(20).sum() + 1e-8)
    data["vwap_dist"] = (close - vwap_approx) / (close + 1e-8)

    # 5. Price Action & Candlestick Metrics
    candle_range = high - low + 1e-8
    body_size = (close - open_).abs()
    data["candle_body_ratio"] = body_size / candle_range
    upper_wick = high - np.maximum(open_, close)
    lower_wick = np.minimum(open_, close) - low
    data["upper_shadow_ratio"] = upper_wick / candle_range
    data["lower_shadow_ratio"] = lower_wick / candle_range
    data["is_bull_candle"] = (close >= open_).astype(float)

    # Consecutive Direction Bars
    direction = np.where(close >= open_, 1, -1)
    consec = np.zeros(len(data))
    curr_streak = 0
    for i in range(len(direction)):
        if i == 0 or np.sign(direction[i]) == np.sign(direction[i-1]):
            curr_streak += direction[i]
        else:
            curr_streak = direction[i]
        consec[i] = curr_streak
    data["consecutive_bars"] = consec

    # 6. Market Regime Dimensions
    # Trend Score: based on ADX and EMA alignment (-1 to +1)
    bull_align = (data["ema_9"] > data["ema_21"]) & (data["ema_21"] > data["ema_50"])
    bear_align = (data["ema_9"] < data["ema_21"]) & (data["ema_21"] < data["ema_50"])
    trend_dir = np.where(bull_align, 1.0, np.where(bear_align, -1.0, 0.0))
    adx_strength = np.clip(data["adx"] / 50.0, 0.0, 1.0)
    data["regime_trend_score"] = trend_dir * adx_strength

    # Volatility Score: ATR vs rolling mean normalized
    data["regime_volatility_score"] = np.clip(data["atr_ratio"] - 1.0, -1.0, 2.0)

    # Chop Score: high when ADX is low and Bollinger bandwidth is compressed
    chop_score = np.clip((30.0 - data["adx"]) / 30.0, 0.0, 1.0) * np.clip(1.0 - data["bb_bandwidth"]*10, 0.0, 1.0)
    data["regime_chop_score"] = chop_score

    # Determine Regime Label
    regimes = []
    for i in range(len(data)):
        t_score = data["regime_trend_score"].iloc[i]
        v_score = data["regime_volatility_score"].iloc[i]
        adx_val = data["adx"].iloc[i]
        
        if adx_val > 28 and t_score > 0.4:
            regimes.append("STRONG_BULL_TREND")
        elif adx_val > 28 and t_score < -0.4:
            regimes.append("STRONG_BEAR_TREND")
        elif v_score > 0.6:
            regimes.append("HIGH_VOLATILITY_BREAKOUT")
        elif adx_val < 20 and abs(t_score) < 0.2:
            regimes.append("RANGING_CHOP")
        elif data["bb_bandwidth"].iloc[i] < 0.02:
            regimes.append("VOLATILITY_COMPRESSION")
        else:
            regimes.append("NEUTRAL_FLOW")
            
    data["regime_label"] = regimes

    # Fill NaN and Inf safely
    data = data.ffill().bfill().fillna(0)
    data = data.replace([np.inf, -np.inf], 0)

    return data

def extract_features_vector(row: pd.Series) -> np.ndarray:
    """Extracts numeric feature array for ML model prediction."""
    vals = []
    for col in FEATURE_COLUMNS:
        v = row.get(col, 0.0)
        try:
            val = float(v)
            if np.isnan(val) or np.isinf(val):
                val = 0.0
        except (ValueError, TypeError):
            val = 0.0
        vals.append(val)
    return np.array(vals, dtype=np.float32)
