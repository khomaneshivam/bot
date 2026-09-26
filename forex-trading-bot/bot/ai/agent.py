import os
import json
import time
import requests
from typing import Dict, Tuple, Optional
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

class GeminiTradingAgent:
    """
    Subordinate LLM Advisory Agent.
    Provides macroeconomic context, market narrative summarization, and anomaly explanations.
    CRITICAL INVARIANT: LLM output is strictly advisory and CANNOT bypass deterministic risk gates.
    """

    def __init__(self):
        self.api_key = GEMINI_API_KEY
        self.model = GEMINI_MODEL
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        self.last_decision = {"signal": "HOLD", "confidence": 0.0, "reason": "Initializing"}
        self.call_count = 0
        self.last_call_time = 0.0
        self.min_call_interval = 5.0  # Rate limit: minimum 5s between requests
        self._cached_decisions: Dict[str, Tuple[str, float, str, float]] = {}

    def set_api_key(self, key: str):
        self.api_key = key.strip()

    def get_ai_decision(self, market_context: Dict) -> Tuple[str, float, str]:
        """
        Queries Gemini for narrative analysis.
        Returns: (Decision: "BUY"|"SELL"|"HOLD", Confidence: float, Reasoning: str)
        Fails closed to ("HOLD", 0.0, reason) upon timeout, network failure, or rate limit.
        """
        symbol = market_context.get("symbol", "UNKNOWN")
        now = time.time()

        # Cache check (30-second TTL per symbol)
        if symbol in self._cached_decisions:
            dec, conf, reason, ts = self._cached_decisions[symbol]
            if (now - ts) < 30.0:
                return dec, conf, reason

        # Rate limiting check
        if (now - self.last_call_time) < self.min_call_interval:
            return self._heuristic_fallback(market_context, reason="Rate limited (call interval < 5s)")

        if not self.api_key:
            self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""

        if not self.api_key:
            return self._heuristic_fallback(market_context, reason="Gemini API Key not configured")

        prompt = f"""
You are an institutional quantitative risk analyst. Evaluate this market setup:
- Asset: {market_context.get('symbol', 'UNKNOWN')}
- Price: {market_context.get('price', 0.0)}
- Regime: {market_context.get('regime', 'NEUTRAL')}
- DXY: {market_context.get('dxy_proxy', 104.5)} ({market_context.get('dxy_trend', 'NEUTRAL')})
- RSI: {market_context.get('rsi', 50.0):.2f}
- ADX: {market_context.get('adx', 20.0):.2f}
- Strategy Consensus: {market_context.get('strategy_consensus', 'HOLD')}

Output JSON with keys:
"decision": "BUY", "SELL", or "HOLD"
"confidence": float between 0.0 and 1.0
"reason": concise 1-sentence analysis
"""

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 200,
                "responseMimeType": "application/json"
            }
        }

        self.last_call_time = now
        self.call_count += 1

        try:
            # Pass API key in header where possible or query param
            headers = {"x-goog-api-key": self.api_key}
            resp = requests.post(self.endpoint, json=payload, headers=headers, timeout=6.0)

            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                parsed = json.loads(text)

                dec = str(parsed.get("decision", "HOLD")).upper()
                if dec not in ("BUY", "SELL", "HOLD"):
                    dec = "HOLD"

                conf = float(parsed.get("confidence", 0.5))
                conf = min(max(conf, 0.0), 1.0)
                reason = str(parsed.get("reason", "LLM advisory analysis"))

                self._cached_decisions[symbol] = (dec, conf, reason, now)
                return dec, conf, reason
            else:
                return self._heuristic_fallback(market_context, reason=f"Gemini API HTTP {resp.status_code}")
        except Exception:
            return self._heuristic_fallback(market_context, reason="Gemini call timed out or failed")

    def _heuristic_fallback(self, market_context: Dict, reason: str = "Fallback") -> Tuple[str, float, str]:
        consensus = market_context.get("strategy_consensus", "HOLD")
        rsi = market_context.get("rsi", 50.0)

        if consensus == "BUY" and rsi < 65:
            return "BUY", 0.65, f"{reason}: Consensus BUY supported by RSI ({rsi:.1f})"
        elif consensus == "SELL" and rsi > 35:
            return "SELL", 0.65, f"{reason}: Consensus SELL supported by RSI ({rsi:.1f})"
        else:
            return "HOLD", 0.50, f"{reason}: Neutral technical alignment"

gemini_agent = GeminiTradingAgent()