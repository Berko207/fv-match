"""Best-effort read-only Polymarket Gamma client for live three-way odds.

This is a convenience layer: ``analyze`` works fully offline with manually
supplied odds. When a Gamma market slug/id is available, this fetches the live
outcome prices and converts them to decimal odds. Auto-discovery via search is
intentionally conservative and degrades gracefully (returns ``None``) — never
raises into the analysis path.

Two market shapes are supported:

* A single three-way moneyline market with ``outcomes`` ``[Home, Draw, Away]``
  (:func:`fetch_three_way_odds`).
* The shape Polymarket actually uses for football matches: one *event* holding
  three separate Yes/No markets — "Will <home> win?", "… end in a draw?", "Will
  <away> win?" — whose ``Yes`` prices are the H/D/A implied probabilities
  (:func:`fetch_match_odds`, the cross-market reader).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
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
    """Search Gamma events (best-effort). Returns raw event dicts.

    Note: the Gamma ``/public-search`` endpoint respects the query far better
    than ``/events?search=`` for free-text discovery.
    """
    try:
        data = _get("/public-search", {"q": query, "limit_per_type": limit})
    except (httpx.HTTPError, ValueError):
        return []
    if isinstance(data, dict):
        events = data.get("events")
        return events if isinstance(events, list) else []
    return data if isinstance(data, list) else []


# --- Cross-market three-way reader (one event, three Yes/No legs) ------------


@dataclass(frozen=True)
class MatchOdds:
    """Three-way decimal odds assembled from an event's Yes/No legs."""

    home_team: str
    away_team: str
    home_odds: float
    draw_odds: float
    away_odds: float
    min_liquidity_usd: float


def _name_tokens(name: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", name.lower())) - {"vs", "fc", "afc"}


def _split_title(title: str) -> tuple[str, str] | None:
    """Split a "Home vs. Away" event title into (home, away)."""
    for sep in (" vs. ", " vs ", " v. ", " v "):
        if sep in title:
            home, away = title.split(sep, 1)
            home, away = home.strip(), away.strip()
            if home and away:
                return home, away
    return None


def _classify_leg(question: str, slug: str, home: str, away: str) -> str | None:
    """Map a Yes/No leg to ``"home"``/``"draw"``/``"away"`` (draw checked first)."""
    q = question.lower()
    s = slug.lower()
    if "draw" in q or "tie" in q or s.endswith("-draw"):
        return "draw"
    q_tokens = set(re.findall(r"[a-z0-9]+", q))
    home_t, away_t = _name_tokens(home), _name_tokens(away)
    home_in = bool(home_t) and home_t <= q_tokens
    away_in = bool(away_t) and away_t <= q_tokens
    if home_in and not away_in:
        return "home"
    if away_in and not home_in:
        return "away"
    return None


def _yes_price(market: dict[str, Any]) -> float | None:
    outcomes = [str(o).strip().casefold() for o in _as_list(market.get("outcomes"))]
    prices_raw = _as_list(market.get("outcomePrices"))
    if len(outcomes) != len(prices_raw) or len(outcomes) < 2:
        return None
    for label, price in zip(outcomes, prices_raw, strict=True):
        if label == "yes":
            try:
                value = float(price)
            except (TypeError, ValueError):
                return None
            return value if value > 0 else None
    return None


def _leg_liquidity(market: dict[str, Any]) -> float:
    for key in ("liquidityNum", "liquidity", "volumeNum", "volume"):
        value = market.get(key)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
    return 0.0


def fetch_event_by_slug(slug: str) -> dict[str, Any] | None:
    """Fetch a single Gamma event (with its nested markets) by slug."""
    try:
        data = _get("/events", {"slug": slug})
    except (httpx.HTTPError, ValueError):
        return None
    if isinstance(data, list) and data:
        first = data[0]
        return first if isinstance(first, dict) else None
    if isinstance(data, dict):
        return data
    return None


def parse_match_odds(
    event: dict[str, Any],
    home: str | None = None,
    away: str | None = None,
) -> MatchOdds | None:
    """Assemble :class:`MatchOdds` from an event's three Yes/No legs.

    ``home``/``away`` default to the two sides parsed from the event title.
    Returns ``None`` unless all three legs (home win, draw, away win) resolve to
    positive prices.
    """
    if home is None or away is None:
        names = _split_title(str(event.get("title") or ""))
        if names is None:
            return None
        home, away = names

    legs: dict[str, tuple[float, float]] = {}  # outcome -> (decimal_odds, liquidity)
    for market in event.get("markets") or []:
        if not isinstance(market, dict) or market.get("closed"):
            continue
        yes = _yes_price(market)
        if yes is None:
            continue
        key = _classify_leg(
            str(market.get("question") or ""), str(market.get("slug") or ""), home, away
        )
        if key is None or key in legs:
            continue
        legs[key] = (1.0 / yes, _leg_liquidity(market))

    if not {"home", "draw", "away"} <= legs.keys():
        return None
    return MatchOdds(
        home_team=home,
        away_team=away,
        home_odds=legs["home"][0],
        draw_odds=legs["draw"][0],
        away_odds=legs["away"][0],
        min_liquidity_usd=min(liq for _, liq in legs.values()),
    )


def fetch_match_odds(
    event_slug: str,
    home: str | None = None,
    away: str | None = None,
) -> MatchOdds | None:
    """Fetch + parse three-way odds for a football-match *event* slug.

    Example slug: ``fifwc-col-cdr-2026-06-23`` (Colombia vs. DR Congo).
    """
    event = fetch_event_by_slug(event_slug)
    if event is None:
        return None
    return parse_match_odds(event, home, away)
