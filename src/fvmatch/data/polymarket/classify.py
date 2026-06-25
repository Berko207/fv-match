"""Classify a raw Polymarket market into a :class:`MarketType` + params.

Polymarket football sub-markets are mostly two-way (Yes/No or Over/Under) and
self-describe in their ``question`` / ``slug``. This module turns one of those
into a normalized :class:`~fvmatch.data.polymarket.taxonomy.MarketLine` via
regex heuristics, mapping each raw outcome label to a canonical pricer key.

Design choices:

* **Question/slug regex, not a single Gamma field.** Gamma's own
  ``sportsMarketType`` is inconsistent across market families, so we read the
  human question (with the slug as a fallback) — robust to either being present.
* **Fail soft.** Anything unrecognized becomes :attr:`MarketType.UNKNOWN` and is
  still carried through as a read-only signal — never dropped, never guessed.

The full-time 1X2 moneyline is assembled separately in
:mod:`fvmatch.data.polymarket.game` from the main event's three Yes/No legs;
this classifier handles the per-market (typically two-way) surface.

NOTE: the patterns are seeded from observed CZE-MEX questions and must be
validated against the live surface; extend ``_RULES`` as new shapes appear.
"""

from __future__ import annotations

import re

from fvmatch.data.polymarket.taxonomy import (
    MarketLine,
    MarketParams,
    MarketType,
    Outcome,
)

# Over/Under and Yes/No canonical mappings (raw label.casefold() -> key)
_OVER = {"over", "yes"}
_UNDER = {"under", "no"}


def _num(pattern: str, text: str) -> float | None:
    m = re.search(pattern, text)
    return float(m.group(1)) if m else None


def _name_tokens(name: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", name.lower())) - {"vs", "fc", "afc", "the"}


def _which_side(text: str, home: str, away: str) -> str | None:
    """Return 'home'/'away' if exactly one team's name tokens appear in ``text``."""
    toks = set(re.findall(r"[a-z0-9]+", text.lower()))
    h = bool(_name_tokens(home)) and _name_tokens(home) <= toks
    a = bool(_name_tokens(away)) and _name_tokens(away) <= toks
    if h and not a:
        return "home"
    if a and not h:
        return "away"
    return None


def _period(text: str) -> str:
    t = text.lower()
    if "1st half" in t or "first half" in t or "-1h" in t or "half-time" in t:
        return "1h"
    if "2nd half" in t or "second half" in t or "-2h" in t:
        return "2h"
    return "full"


def _line_value(text: str) -> float | None:
    """Extract an over/under threshold like 'over 8.5' / 'o2.5' / '2.5 goals'."""
    for pat in (
        r"(?:over|under|o/u|total)\D{0,6}(\d+\.?\d*)",
        r"(\d+\.?\d*)\s*(?:goals|corners|shots|assists)",
        r"\b(\d+\.?\d*)\b",
    ):
        v = _num(pat, text.lower())
        if v is not None:
            return v
    return None


def _exact_score(text: str, home: str, away: str) -> tuple[int, int] | None:
    """Parse 'Czechia 0-1 Mexico' / '0-1' into (home_goals, away_goals).

    Strips ISO dates first so '2026-06-24' isn't mistaken for a scoreline, and
    only accepts single-digit goals (football scorelines, not years).
    """
    cleaned = re.sub(r"\d{4}-\d{2}-\d{2}", " ", text)
    m = re.search(r"\b(\d)\s*[-:]\s*(\d)\b", cleaned)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _map_over_under(outcomes: list[Outcome]) -> list[Outcome]:
    out: list[Outcome] = []
    for o in outcomes:
        lab = o.label.strip().casefold()
        key = "over" if lab in _OVER else "under" if lab in _UNDER else None
        out.append(Outcome(o.label, o.price, o.decimal_odds, key, o.token_id))
    return out


def _map_yes_no(outcomes: list[Outcome]) -> list[Outcome]:
    out: list[Outcome] = []
    for o in outcomes:
        lab = o.label.strip().casefold()
        key = "yes" if lab in _OVER else "no" if lab in _UNDER else None
        out.append(Outcome(o.label, o.price, o.decimal_odds, key, o.token_id))
    return out


def classify_market(
    question: str,
    slug: str,
    outcomes: list[Outcome],
    home: str,
    away: str,
    *,
    event_id: str | int | None = None,
    condition_id: str | None = None,
    liquidity_usd: float = 0.0,
    raw_sports_market_type: str | None = None,
) -> MarketLine:
    """Classify one Polymarket market into a normalized :class:`MarketLine`."""
    text = f"{question} {slug}".lower()
    period = _period(text)
    side = _which_side(question, home, away)

    market_type = MarketType.UNKNOWN
    params = MarketParams(period=period, side=side)
    mapped = outcomes

    if "corner" in text:
        line = _line_value(text)
        if period != "full":
            market_type = MarketType.HALF_TOTAL_CORNERS
        elif side:
            market_type = MarketType.TEAM_TOTAL_CORNERS
        else:
            market_type = MarketType.TOTAL_CORNERS
        params = MarketParams(line=line, side=side, period=period)
        mapped = _map_over_under(outcomes)
    elif "shot" in text:
        line = _line_value(text)
        market_type = MarketType.TEAM_TOTAL_SHOTS if side else MarketType.TOTAL_SHOTS
        params = MarketParams(line=line, side=side, period=period)
        mapped = _map_over_under(outcomes)
    elif "assist" in text:
        line = _line_value(text)
        market_type = (
            MarketType.TEAM_TOTAL_ASSISTS if side else MarketType.TOTAL_ASSISTS
        )
        params = MarketParams(line=line, side=side, period=period)
        mapped = _map_over_under(outcomes)
    elif "both teams to score" in text or "btts" in text:
        market_type = MarketType.BOTH_TEAMS_TO_SCORE
        params = MarketParams(period=period)
        mapped = _map_yes_no(outcomes)
    elif "clean sheet" in text:
        market_type = MarketType.CLEAN_SHEET
        params = MarketParams(side=side, period=period)
        mapped = _map_yes_no(outcomes)
    elif "exact score" in text or "correct score" in text:
        score = _exact_score(question, home, away)
        market_type = MarketType.EXACT_SCORE
        params = MarketParams(
            home=score[0] if score else None,
            away=score[1] if score else None,
            period=period,
        )
        mapped = _map_yes_no(outcomes)
    elif "odd or even" in text or re.search(r"\bodd\b|\beven\b", text):
        market_type = MarketType.ODD_EVEN_GOALS
        params = MarketParams(period=period)
        # canonical keys odd/even assigned from labels directly
        mapped = [
            Outcome(
                o.label,
                o.price,
                o.decimal_odds,
                "odd" if "odd" in o.label.lower() else "even",
                o.token_id,
            )
            for o in outcomes
        ]
    elif "win by" in text or "winning margin" in text or "margin" in text:
        market_type = MarketType.WINNING_MARGIN
        params = MarketParams(line=_line_value(text), side=side, period=period)
        mapped = _map_yes_no(outcomes)
    elif period != "full" and ("result" in text or " win" in text or "winner" in text):
        market_type = MarketType.HALF_RESULT
        params = MarketParams(period=period)
    elif "total" in text or "over" in text or "under" in text or re.search(
        r"\d+\.\d", text
    ):
        # generic goals total (no corner/shot/assist keyword reached here)
        line = _line_value(text)
        if period != "full":
            market_type = MarketType.HALF_TOTAL_GOALS
        elif side:
            market_type = MarketType.TEAM_TOTAL_GOALS
        else:
            market_type = MarketType.TOTAL_GOALS
        params = MarketParams(line=line, side=side, period=period)
        mapped = _map_over_under(outcomes)

    return MarketLine(
        market_type=market_type,
        params=params,
        outcomes=mapped,
        question=question,
        slug=slug,
        event_id=event_id,
        condition_id=condition_id,
        liquidity_usd=liquidity_usd,
        raw_sports_market_type=raw_sports_market_type,
    )
