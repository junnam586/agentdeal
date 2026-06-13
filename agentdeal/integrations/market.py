"""Bright Data adapter - the real market reference price.

This is what turns "saved X%" into a real number: before negotiation begins we
fetch the going rate for the resource via Bright Data's SERP API so savings are
grounded, not invented.

Internal contract:
    get_market_reference(resource_query: str) -> MarketReference
where ``MarketReference`` carries ``price: float`` and ``sources: list[str]``.

Called exactly once per negotiation, off the per-turn loop. We query Google
through the SERP API (parsed JSON via ``brd_json=1``), extract price tokens from
the results, drop outliers, and use the median as a representative going rate.
Without a key it returns a clearly-labeled offline reference (~$50).
"""

from __future__ import annotations

import json
import re
import statistics
import urllib.parse

import httpx
from pydantic import BaseModel

from ..config import env

# Offline baseline for the tuned scenario (~$50 going rate).
OFFLINE_REFERENCE = 50.0

# Target the *consumer dataset-subscription* tier (what a buyer actually pays for
# a single curated dataset), not enterprise data-report pricing. This range drops
# both per-record/trial noise (sub-$20) and enterprise reports ($500+), so the
# median reflects a realistic consumer going rate.
_MIN_PRICE = 20.0
_MAX_PRICE = 300.0

_PRICE_RE = re.compile(r"\$([0-9][0-9,]*(?:\.[0-9]{1,2})?)")

# Consumer-oriented query templates (run + aggregated for reliability). The
# generic "dataset/data ... price" terms live in the templates, so the keywords
# are just the domain core (e.g. "restaurant").
_QUERY_TEMPLATES = [
    "{kw} dataset subscription price",
    "{kw} data marketplace price per month",
]

# Words dropped from the resource to leave the domain core: filler + generic
# data words (so "APAC restaurant-pricing dataset" -> "APAC restaurant", which
# surfaces consumer marketplace listings instead of enterprise data reports).
_DROP_WORDS = {
    "access", "to", "a", "an", "the", "of", "for", "with", "curated", "get", "buy",
    "dataset", "datasets", "data", "pricing", "price", "prices", "curated",
}


def _keywords(resource: str) -> str:
    words = [w for w in re.split(r"[^A-Za-z0-9]+", resource) if w and w.lower() not in _DROP_WORDS]
    return " ".join(words) or resource


class MarketReference(BaseModel):
    price: float
    sources: list[str] = []


def brightdata_available() -> bool:
    return env("BRIGHTDATA_API_KEY") is not None


def _offline(note: str) -> MarketReference:
    return MarketReference(price=OFFLINE_REFERENCE, sources=[note])


def get_market_reference(resource_query: str) -> MarketReference:
    """Fetch the real consumer going rate for ``resource_query`` via Bright Data.

    Runs a couple of consumer-oriented SERP queries and aggregates the in-tier
    prices for reliability (a single query is noisy / can time out).
    """
    api_key = env("BRIGHTDATA_API_KEY")
    zone = env("BRIGHTDATA_ZONE")
    if not api_key or not zone:
        return _offline("offline reference (Bright Data not configured)")

    kw = _keywords(resource_query)
    prices: list[float] = []
    sources: list[str] = []
    for template in _QUERY_TEMPLATES:
        q = urllib.parse.quote_plus(template.format(kw=kw))
        search_url = f"https://www.google.com/search?q={q}&brd_json=1"
        try:
            resp = httpx.post(
                "https://api.brightdata.com/request",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"zone": zone, "url": search_url, "format": "raw"},
                timeout=45.0,
            )
            resp.raise_for_status()
        except httpx.HTTPError:
            continue  # try the next query variant
        p, s = _parse_prices(resp.text)
        prices.extend(p)
        for dom in s:
            if dom not in sources:
                sources.append(dom)

    if not prices:
        return _offline("Bright Data returned no consumer-tier price; using offline reference")
    # Median is robust to the spread of unrelated prices across results.
    return MarketReference(price=round(statistics.median(prices), 2), sources=sources[:4] or ["Bright Data SERP (google.com)"])


def _parse_prices(raw: str) -> tuple[list[float], list[str]]:
    """Extract in-tier prices + source domains from a SERP response."""
    sources: list[str] = []
    try:
        data = json.loads(raw)
        for item in (data.get("organic") or [])[:4]:
            # Prefer the clean, clickable URL over the breadcrumb display_link.
            link = item.get("link") or item.get("source") or item.get("display_link")
            if link:
                sources.append(str(link))
    except (json.JSONDecodeError, AttributeError):
        pass  # fall back to scanning the raw text for prices

    prices: list[float] = []
    for m in _PRICE_RE.findall(raw):
        try:
            val = float(m.replace(",", ""))
        except ValueError:
            continue
        if _MIN_PRICE <= val <= _MAX_PRICE:
            prices.append(val)
    return prices, sources
