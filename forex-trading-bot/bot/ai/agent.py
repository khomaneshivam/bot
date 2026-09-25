import os
import json
import time
import requests
from typing import Dict, Tuple, Optional
from dotenv import load_dotenv

# Load local .env file
load_dotenv()

# Gemini API configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

class GeminiTradingAgent:
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        self.model = GEMINI_MODEL
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        self.last_decision = {"signal": "HOLD", "confidence": 0.0, "reason": "Initializing Gemini"}
        self.call_count = 0
        self.last_call_time = 0.0

    def set_api_key(self, key: str):
        """Allows dynamic API key update at runtime."""
        self.api_key = key.strip()

    def get_ai_decision(self, market_context: Dict) -> Tuple[str, float, str]:
        """
        Queries Google Gemini LLM for institutional quantitative market evaluation.
        
        market_context = {
            "symbol": str,
            "price": float,
            "regime": str,
            "dxy_proxy": float,
            "dxy_trend": str,
            "ema50": float,
            "ema200": float,
            "rsi": float,
            "macd_diff": float,
            "adx": float,
            "strategy_consensus": str,
            "wrong_trades_lessons": list
        }
        
        Returns: (Decision: "BUY"|"SELL"|"HOLD", Confidence: float, Reasoning: str)
        """
        # Re-check environment key if not set
        if not self.api_key:
            self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""

        # If no Gemini API key configured, use quantitative heuristic fallback
        if not self.api_key:
            return self._heuristic_fallback(market_context, reason="Gemini API Key pending in .env")

        prompt = f"""
You are an institutional quantitative trading risk analyst. Evaluate this market setup and provide your trade decision.

### MARKET SNAPSHOT
- Asset: {market_context.get('symbol', 'UNKNOWN')}
- Current Price: {market_context.get('price', 0.0)}
- Market Regime: {market_context.get('regime', 'NEUTRAL')}
- Synthetic US Dollar Index (DXY): {market_context.get('dxy_proxy', 104.5)} ({market_context.get('dxy_trend', 'NEUTRAL')})
- Technical Indicators:
  * RSI (14): {market_context.get('rsi', 50.0):.2f}
  * ADX (Trend Strength): {market_context.get('adx', 20.0):.2f}
  * EMA 50: {market_context.get('ema50', 0.0):.4f} | EMA 200: {market_context.get('ema200', 0.0):.4f}
  * MACD Histogram: {market_context.get('macd_diff', 0.0):.6f}
- Core Strategies Consensus: {market_context.get('strategy_consensus', 'HOLD')}
- Past Mistakes Learned to AVOID: {market_context.get('wrong_trades_lessons', 'None')}

### MANDATORY RULES:
1. Capital preservation is priority #1 (we are using real funds).
2. Never buy into overbought RSI (>70) or sell into oversold RSI (<30).
3. Do not trade against the macro Dollar Index (DXY) trend for USD pairs.
4. Output strict JSON with:
   - "decision": "BUY", "SELL", or "HOLD"
   - "confidence": float between 0.0 and 1.0
   - "reason": concise 1-sentence institutional rationale
"""

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.15,
                "maxOutputTokens": 200,
                "responseMimeType": "application/json"
            }
        }

        url = f"{self.endpoint}?key={self.api_key}"

        try:
            resp = requests.post(url, json=payload, timeout=10.0)
            if resp.status_code == 200:
                result = resp.json()
                text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                if "{" in text and "}" in text:
                    text = text[text.find("{"):text.rfind("}")+1]
                data = json.loads(text)

                decision = str(data.get("decision", "HOLD")).upper()
                confidence = float(data.get("confidence", 0.5))
                reason = str(data.get("reason", "Gemini neural evaluation"))

                if decision not in ["BUY", "SELL", "HOLD"]:
                    decision = "HOLD"

                self.last_decision = {"signal": decision, "confidence": confidence, "reason": reason}
                self.call_count += 1
                self.last_call_time = time.time()
                return decision, confidence, f"Gemini: {reason}"
            else:
                err_msg = f"Gemini API HTTP {resp.status_code}: {resp.text[:100]}"
                return self._heuristic_fallback(market_context, reason=err_msg)

        except Exception as e:
            return self._heuristic_fallback(market_context, reason=f"Gemini connection note: {e}")

    def _heuristic_fallback(self, ctx: Dict, reason: str = "") -> Tuple[str, float, str]:
        """High-probability quantitative fallback when API call is unavailable or rate-limited."""
        base_sig = ctx.get("strategy_consensus", "HOLD")
        rsi = ctx.get("rsi", 50.0)

        # Basic safety filters
        if base_sig == "BUY" and rsi < 68:
            return "BUY", 0.78, f"Quantitative Guard: Confirmed ({reason})"
        elif base_sig == "SELL" and rsi > 32:
            return "SELL", 0.78, f"Quantitative Guard: Confirmed ({reason})"
        else:
            return "HOLD", 0.50, f"Neutral Market Filter ({reason})"

gemini_agent = GeminiTradingAgent()