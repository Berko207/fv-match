"""Best-effort read-only Polymarket Gamma client for live three-way odds.

This is a convenience layer: ``analyze`` works fully offline with manually
supplied odds. When a Gamma market slug/id is available, this fetches the live
outcome prices and converts them to decimal odds. Auto-discovery via search is
intentionally conservative and degrades gracefully (returns ``None``) — never
raises into the analysis path.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

GAMMA_BASE = "https://gamma-api.polymarket.com"
_TIMEOUT = 15.0

_HOME_TOKENS = {"home", "1", "host"}
_DRAW_TOKENS = {"draw", "tie", "x"}
_AWAY_TOKENS = {"away", "2", "visitor"}


def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    url = f"{GAMMA_BASE}{path}"
    resp = httpx.get(url, params=params, timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return []


def fetch_market_by_slug(slug: str) -> dict[str, Any] | None:
    """Fetch a single Gamma market by slug, or ``None`` if not found."""
    try:
        data = _get("/markets", {"slug": slug})
    except (httpx.HTTPError, ValueError):
        return None
    if isinstance(data, list) and data:
        first = data[0]
        return first if isinstance(first, dict) else None
    if isinstance(data, dict):
        return data
    return None


def parse_three_way_odds(market: dict[str, Any]) -> dict[str, float] | None:
    """Extract ``{home, draw, away}`` decimal odds from a Gamma market.

    Expects matching ``outcomes`` and ``outcomePrices`` arrays where each price
    is an implied probability in (0, 1). Returns ``None`` if the market is not a
    recognizable three-way moneyline.
    """
    outcomes = [str(o).strip().casefold() for o in _as_list(market.get("outcomes"))]
    prices_raw = _as_list(market.get("outcomePrices"))
    if len(outcomes) != len(prices_raw) or len(outcomes) < 2:
        return None
    try:
        prices = [float(p) for p in prices_raw]
    except (TypeError, ValueError):
        return None

    mapping: dict[str, float] = {}
    for label, price in zip(outcomes, prices, strict=True):
        if price <= 0:
            continue
        odds = 1.0 / price
        if label in _HOME_TOKENS or "home" in label:
            mapping["home"] = odds
        elif label in _DRAW_TOKENS or "draw" in label or "tie" in label:
            mapping["draw"] = odds
        elif label in _AWAY_TOKENS or "away" in label:
            mapping["away"] = odds
    if {"home", "draw", "away"} <= mapping.keys():
        return mapping
    return None


def fetch_three_way_odds(slug: str) -> dict[str, float] | None:
    """Fetch + parse three-way decimal odds for a Gamma market slug."""
    market = fetch_market_by_slug(slug)
    if market is None:
        return None
    return parse_three_way_odds(market)


def search_events(query: str, limit: int = 20) -> list[dict[str, Any]]:
    """Search Gamma events (best-effort). Returns raw event dicts."""
    try:
        data = _get("/events", {"search": query, "limit": limit, "closed": "false"})
    except (httpx.HTTPError, ValueError):
        return []
    return data if isinstance(data, list) else []
