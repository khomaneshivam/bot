def generate_signal(df, rsi_overbought=70, rsi_oversold=30):
    last = df.iloc[-1]

    if last["ema50"] > last["ema200"] and last["rsi"] < rsi_overbought:
        return "BUY"

    if last["ema50"] < last["ema200"] and last["rsi"] > rsi_oversold:
        return "SELL"

    return "HOLD"