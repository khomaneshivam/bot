import time
import urllib.request
import xml.etree.ElementTree as ET
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field

class MacroEvent(BaseModel):
    time_utc: str  # Format: "HH:MM"
    currency: str
    event: str
    impact: str    # "CRITICAL", "HIGH", "MEDIUM", "LOW"
    forecast: str = "-"
    previous: str = "-"

class NewsArticle(BaseModel):
    title: str
    source: str
    link: str
    published: str
    retrieval_timestamp: str
    snippet: str
    sentiment: str
    impact: str
    symbol_relevance: List[str] = Field(default_factory=list)
    confidence: float = 0.8
    freshness_seconds: float = 0.0

class NewsFeedEngine:
    """
    Hardened Macro & News Catalyst Engine.
    Ingests live RSS headlines and manages high-impact economic calendar vetoes.
    NEVER fabricates synthetic headlines.
    Provides deterministic blackout window checking for macroeconomic events.
    """

    def __init__(self):
        self.cached_articles: List[NewsArticle] = []
        self.last_fetch_time: float = 0.0
        self.cache_ttl: float = 60.0
        self.feed_status: str = "INITIALIZING"

        self.bullish_keywords = [
            "rate cut", "dovish", "inflation falls", "cooling inflation", "safe-haven", "gold surges",
            "gold rallies", "dollar weakens", "dollar falls", "fed cuts", "yields drop", "treasury yields fall",
            "stimulus", "banking crisis", "central bank buying", "etf inflows", "bullish momentum"
        ]
        self.bearish_keywords = [
            "rate hike", "hawkish", "hot inflation", "sticky inflation", "yields surge", "yields rise",
            "dollar rallies", "dollar strengthens", "fed pauses cuts", "strong labor", "nfp beats",
            "jobs blowout", "etf outflows", "gold plunges", "gold falls", "tightening", "bearish reversal"
        ]
        self.high_impact_keywords = [
            "fomc", "federal reserve", "cpi", "inflation", "nonfarm payrolls", "nfp", "gdp", "powell",
            "lagarde", "interest rate decision", "core pce", "war", "escalation", "emergency meeting"
        ]

        # Scheduled high-impact macro calendar events (times in UTC)
        self.scheduled_macro_events: List[MacroEvent] = [
            MacroEvent(time_utc="12:30", currency="USD", event="Core CPI / Non-Farm Payrolls", impact="HIGH"),
            MacroEvent(time_utc="14:00", currency="USD", event="ISM Services PMI", impact="HIGH"),
            MacroEvent(time_utc="18:00", currency="USD", event="FOMC Rate Decision / Minutes", impact="CRITICAL"),
            MacroEvent(time_utc="08:00", currency="EUR", event="ECB Rate Decision / Lagarde Speech", impact="HIGH"),
            MacroEvent(time_utc="01:30", currency="JPY", event="BOJ Policy Rate Decision", impact="HIGH")
        ]

    def _analyze_headline(self, text: str) -> Tuple[str, str, List[str], float]:
        lower = text.lower()
        bull_score = sum(1 for kw in self.bullish_keywords if kw in lower)
        bear_score = sum(1 for kw in self.bearish_keywords if kw in lower)
        is_high = any(kw in lower for kw in self.high_impact_keywords)

        impact = "HIGH" if is_high else ("MEDIUM" if (bull_score + bear_score) > 0 else "LOW")

        if bull_score > bear_score:
            sentiment = "BULLISH"
            conf = min(0.95, 0.60 + (bull_score - bear_score) * 0.1)
        elif bear_score > bull_score:
            sentiment = "BEARISH"
            conf = min(0.95, 0.60 + (bear_score - bull_score) * 0.1)
        else:
            sentiment = "NEUTRAL"
            conf = 0.50

        # Symbol relevance mapping
        relevance = []
        if any(w in lower for w in ["gold", "xau", "bullion", "precious metals"]):
            relevance.append("XAUUSD")
        if any(w in lower for w in ["dollar", "dxy", "fed", "fomc", "treasury", "yield"]):
            relevance.extend(["EURUSD", "GBPUSD", "USDJPY", "BTCUSDT", "XAUUSD"])
        if any(w in lower for w in ["euro", "ecb", "lagarde", "germany"]):
            relevance.append("EURUSD")
        if any(w in lower for w in ["bitcoin", "btc", "crypto", "etf", "sec"]):
            relevance.append("BTCUSDT")

        return sentiment, impact, list(set(relevance)), conf

    def fetch_news(self) -> List[NewsArticle]:
        now = time.time()
        if self.cached_articles and (now - self.last_fetch_time) < self.cache_ttl:
            return self.cached_articles

        urls = [
            ("Yahoo Finance Commodities", "https://finance.yahoo.com/news/rssindex"),
            ("ForexLive Macro", "https://www.forexlive.com/feed/news")
        ]

        articles: List[NewsArticle] = []
        retrieval_utc = datetime.now(timezone.utc).isoformat()

        for src_name, url in urls:
            try:
                req = urllib.request.Request(
                    url,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) QuantAI/2.0'}
                )
                with urllib.request.urlopen(req, timeout=4.0) as response:
                    xml_data = response.read()
                    root = ET.fromstring(xml_data)
                    channel = root.find("channel")
                    if channel is not None:
                        items = channel.findall("item")[:8]
                        for it in items:
                            title = it.findtext("title", "").strip()
                            link = it.findtext("link", "").strip()
                            pub_date = it.findtext("pubDate", "")
                            description = it.findtext("description", "")
                            clean_desc = re.sub(r'<[^>]+>', '', description).strip()[:180]

                            if title:
                                sentiment, impact, relevance, conf = self._analyze_headline(title + " " + clean_desc)
                                articles.append(NewsArticle(
                                    title=title,
                                    source=src_name,
                                    link=link,
                                    published=pub_date,
                                    retrieval_timestamp=retrieval_utc,
                                    snippet=clean_desc,
                                    sentiment=sentiment,
                                    impact=impact,
                                    symbol_relevance=relevance,
                                    confidence=conf,
                                    freshness_seconds=0.0
                                ))
            except Exception:
                pass

        if articles:
            self.cached_articles = articles
            self.last_fetch_time = now
            self.feed_status = "ONLINE"
        else:
            if not self.cached_articles:
                self.feed_status = "UNAVAILABLE"
            else:
                self.feed_status = "STALE"

        return self.cached_articles

    def is_macro_blackout_active(
        self,
        symbol: str,
        current_dt_utc: Optional[datetime] = None,
        pre_event_minutes: int = 15,
        post_event_minutes: int = 15
    ) -> Tuple[bool, Optional[str]]:
        """
        Determines whether high-impact macroeconomic event blackout window is active.
        If active, new order execution should be vetoed by risk controls.
        """
        if current_dt_utc is None:
            current_dt_utc = datetime.now(timezone.utc)

        clean_sym = symbol.upper().replace("-", "").replace("/", "")

        # Determine which currencies affect this symbol
        affected_currencies = ["USD"]
        if "EUR" in clean_sym:
            affected_currencies.append("EUR")
        if "GBP" in clean_sym:
            affected_currencies.append("GBP")
        if "JPY" in clean_sym:
            affected_currencies.append("JPY")

        curr_time = current_dt_utc.time()

        for event in self.scheduled_macro_events:
            if event.impact not in ("HIGH", "CRITICAL"):
                continue
            if event.currency not in affected_currencies:
                continue

            try:
                ev_hour, ev_min = map(int, event.time_utc.split(":"))
                event_datetime = current_dt_utc.replace(hour=ev_hour, minute=ev_min, second=0, microsecond=0)

                start_window = event_datetime - timedelta(minutes=pre_event_minutes)
                end_window = event_datetime + timedelta(minutes=post_event_minutes)

                if start_window <= current_dt_utc <= end_window:
                    mins_diff = int((event_datetime - current_dt_utc).total_seconds() / 60)
                    if mins_diff >= 0:
                        reason = f"Macro Blackout: {event.impact} impact {event.event} ({event.currency}) in {mins_diff}m"
                    else:
                        reason = f"Macro Blackout: {event.impact} impact {event.event} ({event.currency}) occurred {abs(mins_diff)}m ago"
                    return True, reason
            except Exception:
                pass

        return False, None

    def evaluate_news_volatility_shield(
        self,
        symbol: str,
        current_dt_utc: Optional[datetime] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Evaluates news & macro volatility shield for candidate symbol.
        Returns (is_vetoed: bool, reason: Optional[str]).
        """
        return self.is_macro_blackout_active(symbol, current_dt_utc)

    def get_news_telemetry(self) -> Dict:
        """Returns structured macro and news telemetry for the dashboard."""
        articles = self.fetch_news()
        return {
            "feed_status": self.feed_status,
            "articles_count": len(articles),
            "articles": [a.model_dump() if hasattr(a, "model_dump") else a.dict() for a in articles[:10]],
            "macro_events": [e.model_dump() if hasattr(e, "model_dump") else e.dict() for e in self.scheduled_macro_events]
        }

news_feed = NewsFeedEngine()
news_feed_engine = news_feed
