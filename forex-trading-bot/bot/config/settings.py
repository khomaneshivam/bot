import os
from typing import Literal
from dotenv import load_dotenv

load_dotenv()

# Operational Modes: "paper" (Paper Trading Simulation), "demo" (Broker Demo / Testnet), "live" (Real Account)
TradingMode = Literal["paper", "demo", "live"]

class Settings:
    # Active Trading Mode
    MODE: TradingMode = "paper"
    
    # Paper Trading Defaults
    PAPER_STARTING_BALANCE = 100.0  # USD
    PAPER_SLIPPAGE_POINTS = 1.5
    PAPER_SPREAD_POINTS = 1.0
    
    # Active Symbol & Market
    # Supported Forex: "EURUSD", "GBPUSD", "USDJPY", "XAUUSD" (Gold), "AUDUSD"
    # Supported Crypto: "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT"
    DEFAULT_SYMBOL = "BTCUSDT"
    DEFAULT_TIMEFRAME = "5m"  # 1m, 5m, 15m, 1h
    BARS_COUNT = 500
    
    # Autonomous Engine Setting
    AUTONOMOUS_ENABLED = True
    AUTONOMOUS_INTERVAL_SEC = 4.0  # Cycle check interval in seconds
    AUDIT_TRADE_MIN_CHANCE_PCT = 45  # Minimum probability from 1-min audit scanner to trigger autonomous trade
    AUDIT_TRADE_ENABLED = True
    
    # Risk Management for $100 Account
    MAX_RISK_PER_TRADE_PERCENT = 2.0  # 2.0% account equity risk per trade ($2.00 on $100 capital)
    DEFAULT_LOT_FOREX = 0.01          # Micro-lots for Forex (0.01 lot = $0.10/pip, 20-pip SL = $2.00)
    DEFAULT_QTY_CRYPTO = 0.0002       # Default crypto fraction (~$12-$15 notional position)
    STOP_LOSS_ATR_MULT = 1.8          # ATR multiple for dynamic Stop Loss
    TAKE_PROFIT_ATR_MULT = 3.6        # ATR multiple for dynamic Take Profit (1:2 Risk/Reward)
    MAX_DAILY_DRAWDOWN_PERCENT = 5.0  # Kill switch threshold if daily equity drops 5%
    MAX_OPEN_POSITIONS = 3
    TRAILING_STOP_ENABLED = True
    TRAILING_STOP_ACTIVATION_R = 1.5  # Activate trailing stop when profit >= 1.5R
    
    # Strategies Enabled
    ENABLE_TREND_STRATEGY = True
    ENABLE_MEAN_REVERSION = True
    ENABLE_BREAKOUT_STRATEGY = True
    ENABLE_SMC_STRATEGY = True
    ENABLE_AI_PREDICTOR = True
    
    # AI & Retraining Settings
    MODEL_RETRAIN_INTERVAL_BARS = 60      # Retrain every 60 bars on live incoming data
    AUTO_RETRAIN_ON_WRONG_TRADE = True   # Automatically retrain when a trade hits loss
    MISTAKE_PENALTY_WEIGHT = 4.0         # Sample weight multiplier for wrong-trade feature patterns
    NEGATIVE_SHIELD_SIMILARITY_THRESHOLD = 0.82  # Cosine similarity above which new trade is vetoed
    
    # MT5 Broker Credentials (Demo / Live)
    MT5_ACCOUNT = int(os.getenv("MT5_ACCOUNT", "0"))
    MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
    MT5_SERVER = os.getenv("MT5_SERVER", "MetaQuotes-Demo")
    MT5_MAGIC_NUMBER = int(os.getenv("MT5_MAGIC_NUMBER", "10001"))
    
    # Crypto Exchange Credentials (Optional for Live/Demo)
    BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
    BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY", "")
    BINANCE_TESTNET = os.getenv("BINANCE_TESTNET", "True").lower() in ("true", "1", "yes")
    
    # Web & Server Settings
    SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
    SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()
