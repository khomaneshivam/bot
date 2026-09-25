import time
try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from bot.config.settings import (
    SYMBOL, TIMEFRAME, BARS, LOT,
    STOP_LOSS_POINTS, TAKE_PROFIT_POINTS,
    RSI_OVERBOUGHT, RSI_OVERSOLD,
    MAGIC_NUMBER, SLEEP_SECONDS
)

from bot.data.data_fetcher import init_mt5, shutdown_mt5, get_rates
from bot.indicators.indicators import add_indicators
from bot.strategies.ema_rsi import generate_signal
from bot.execution.trade_executor import place_trade, has_open_position
from bot.execution.trade_tracker import get_open_positions
from bot.ai.agent import get_ai_decision


def run():
    init_mt5()
    print("Bot started...")

    last_trade_time = 0

    try:
        while True:
            print("\n==============================")

            # 1. Fetch market data
            try:
                df = get_rates(SYMBOL, TIMEFRAME, BARS)
                df = add_indicators(df)
            except Exception as e:
                print("Data fetch error:", e)
                time.sleep(5)
                continue

            # 2. Generate signals (Strategy + AI)
            try:
                last = df.iloc[-1]

                base_signal = generate_signal(df, RSI_OVERBOUGHT, RSI_OVERSOLD)

                market_data = {
                    "price": last["close"],
                    "ema50": last["ema50"],
                    "ema200": last["ema200"],
                    "rsi": last["rsi"],
                    "signal": base_signal
                }

                ai_signal = get_ai_decision(market_data)

                print(f"Base Signal: {base_signal}")
                print(f"AI Decision: {ai_signal}")

                # Final decision
                if ai_signal == base_signal:
                    signal = ai_signal
                else:
                    signal = "HOLD"

                # Extra safety filter
                if market_data["rsi"] > 75 or market_data["rsi"] < 25:
                    print("Extreme RSI → Skipping trade")
                    signal = "HOLD"

            except Exception as e:
                print("Signal error:", e)
                signal = "HOLD"

            # 3. Track live positions
            try:
                positions = get_open_positions(SYMBOL)

                if positions:
                    print("\n--- LIVE POSITIONS ---")
                    for p in positions:
                        print(
                            f"Ticket: {p['ticket']} | "
                            f"Type: {p['type']} | "
                            f"Volume: {p['volume']} | "
                            f"Open: {p['price_open']} | "
                            f"Current: {p['current_price']} | "
                            f"Profit: {p['profit']}"
                        )
                else:
                    print("No open positions")

            except Exception as e:
                print("Tracking error:", e)

            # 4. Execute trade
            if signal != "HOLD" and not has_open_position(SYMBOL):
                if time.time() - last_trade_time > SLEEP_SECONDS:
                    try:
                        result = place_trade(
                            SYMBOL,
                            signal,
                            LOT,
                            STOP_LOSS_POINTS,
                            TAKE_PROFIT_POINTS,
                            MAGIC_NUMBER
                        )

                        print("\nTrade result:", result)

                        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                            print("Trade executed successfully ✅")
                            last_trade_time = time.time()
                        else:
                            print("Trade failed ❌")

                    except Exception as e:
                        print("Execution error:", e)

            # 5. Wait
            time.sleep(SLEEP_SECONDS)

    finally:
        print("Shutting down MT5...")
        shutdown_mt5()


if __name__ == "__main__":
    run()