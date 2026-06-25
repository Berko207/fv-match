"""Full-surface discovery: a Polymarket game slug → a normalized MarketSurface.

A football "game" on Polymarket is spread across many sibling *events* that share
a ``gameId`` (the main event holds only the 3-way moneyline; totals, corners,
exact-score, halves, etc. live in their own events). This module:

1. fetches the main event by slug and reads the two team names from its title,
2. discovers the sibling events for the same game (by ``gameId``, falling back
   to title match) via Gamma search,
3. parses every market into a :class:`MarketLine` — assembling the 3-way
   moneyline from its three Yes/No legs, classifying everything else — and
   returns one :class:`MarketSurface`.

Everything degrades gracefully: if sibling discovery fails or the API is
unreachable, you still get a surface with whatever was fetched (at minimum the
moneyline). Nothing here raises into the analysis path.

The discovery *endpoint* for siblings is best-effort (Gamma's public search);
the per-event parsing is grounded in the real market shape and is the stable
part. Validate sibling coverage against a live game and widen the search if
needed.
"""

from __future__ import annotations

import re

from fvmatch.data.polymarket.classify import classify_market
from fvmatch.data.polymarket.gamma import GammaMarket, _parse_gamma_market
from fvmatch.data.polymarket.odds import (
    _split_title,
    fetch_event_by_slug,
    search_events,
)
from fvmatch.data.polymarket.taxonomy import (
    MarketLine,
    MarketParams,
    MarketType,
    Outcome,
    MarketSurface,
)

_WIN_DRAW = re.compile(r"\bwin\b|\bwins\b|\bto win\b|\bdraw\b|\btie\b", re.IGNORECASE)
_MAX_LINES = 400


def _classify_moneyline_leg(gm: GammaMarket, home: str, away: str) -> str | None:
    """Map a Yes/No leg to 'home'/'draw'/'away' — only if it's a win/draw market.

    Guards against a 'Mexico Total Goals' market being mistaken for the
    'Mexico win' leg: a leg only counts when its question mentions win/draw.
    """
    q = gm.question
    if not _WIN_DRAW.search(q):
        return None
    ql = q.lower()
    if "draw" in ql or "tie" in ql:
        return "draw"
    q_tokens = set(re.findall(r"[a-z0-9]+", ql))
    home_t = set(re.findall(r"[a-z0-9]+", home.lower()))
    away_t = set(re.findall(r"[a-z0-9]+", away.lower()))
    home_in = bool(home_t) and home_t <= q_tokens
    away_in = bool(away_t) and away_t <= q_tokens
    if home_in and not away_in:
        return "home"
    if away_in and not home_in:
        return "away"
    return None


def _assemble_moneyline(
    markets: list[GammaMarket], home: str, away: str
) -> tuple[MarketLine | None, set[str]]:
    """Build a single ONE_X_TWO line from the three Yes/No win/draw legs.

    Returns ``(line_or_none, consumed_condition_ids)``.
    """
    legs: dict[str, Outcome] = {}
    consumed: set[str] = set()
    liquidity: list[float] = []
    for gm in markets:
        if gm.closed:
            continue
        yes = gm.price_for_outcome("Yes")
        if yes is None or yes <= 0:
            continue
        key = _classify_moneyline_leg(gm, home, away)
        if key is None or key in legs:
            continue
        legs[key] = Outcome(
            label=key,
            price=yes,
            decimal_odds=1.0 / yes,
            key=key,
            token_id=gm.token_id_for_outcome("Yes"),
        )
        consumed.add(gm.condition_id or gm.market_id)
        liquidity.append(gm.liquidity_usd)
    if not {"home", "draw", "away"} <= legs.keys():
        return None, set()
    line = MarketLine(
        market_type=MarketType.ONE_X_TWO,
        params=MarketParams(),
        outcomes=[legs["home"], legs["draw"], legs["away"]],
        question=f"{home} vs {away} — match result",
        slug="",
        liquidity_usd=min(liquidity) if liquidity else 0.0,
    )
    return line, consumed


def _market_outcomes(gm: GammaMarket) -> list[Outcome]:
    return [
        Outcome(
            label=label,
            price=price,
            decimal_odds=(1.0 / price) if price > 0 else float("inf"),
            token_id=token,
        )
        for label, price, token in zip(
            gm.outcomes,
            gm.outcome_prices,
            gm.clob_token_ids + ("",) * (len(gm.outcomes) - len(gm.clob_token_ids)),
            strict=False,
        )
    ]


def event_to_lines(event: dict, home: str, away: str) -> list[MarketLine]:
    """Parse one Gamma event's markets into normalized MarketLines."""
    raw_markets = event.get("markets") or []
    gmarkets = [_parse_gamma_market(m) for m in raw_markets if isinstance(m, dict)]

    lines: list[MarketLine] = []
    moneyline, consumed = _assemble_moneyline(gmarkets, home, away)
    if moneyline is not None:
        lines.append(moneyline)

    for gm in gmarkets:
        if gm.closed:
            continue
        if (gm.condition_id or gm.market_id) in consumed:
            continue
        lines.append(
            classify_market(
                gm.question,
                gm.slug,
                _market_outcomes(gm),
                home,
                away,
                event_id=event.get("id"),
                condition_id=gm.condition_id or None,
                liquidity_usd=gm.liquidity_usd,
                raw_sports_market_type=gm.raw.get("sportsMarketType"),
            )
        )
    return lines


def build_surface(
    events: list[dict], home: str, away: str, game_id, slug: str
) -> MarketSurface:
    """Assemble a MarketSurface from already-fetched event dicts (deduped)."""
    seen: set[str] = set()
    lines: list[MarketLine] = []
    for event in events:
        for line in event_to_lines(event, home, away):
            cond = line.condition_id or f"{line.market_type}:{line.question}"
            if cond in seen:
                continue
            seen.add(cond)
            lines.append(line)
            if len(lines) >= _MAX_LINES:
                break
    return MarketSurface(
        home=home, away=away, game_id=game_id, slug=slug, lines=lines
    )


def _discover_sibling_events(home: str, away: str, game_id) -> list[dict]:
    """Best-effort: find sibling events for the same game via Gamma search."""
    query = f"{home} {away}"
    candidates = search_events(query, limit=60)
    siblings: list[dict] = []
    for ev in candidates:
        if not isinstance(ev, dict):
            continue
        same_game = game_id is not None and ev.get("gameId") == game_id
        title = str(ev.get("title") or "")
        names = _split_title(title)
        same_title = names is not None and {
            names[0].lower(),
            names[1].lower(),
        } == {home.lower(), away.lower()}
        if same_game or same_title:
            siblings.append(ev)
    return siblings


def fetch_surface(slug: str) -> MarketSurface | None:
    """Fetch + normalize the entire market surface for a game slug.

    Returns ``None`` only if the main event itself can't be fetched. Sibling
    discovery failures degrade to a moneyline-only surface, never an error.
    """
    main = fetch_event_by_slug(slug)
    if main is None:
        return None
    names = _split_title(str(main.get("title") or ""))
    if names is None:
        return None
    home, away = names
    game_id = main.get("gameId")

    events = [main]
    try:
        siblings = _discover_sibling_events(home, away, game_id)
        seen_ids = {main.get("id")}
        for ev in siblings:
            if ev.get("id") not in seen_ids:
                events.append(ev)
                seen_ids.add(ev.get("id"))
    except Exception:  # noqa: BLE001 - discovery is best-effort
        pass

    return build_surface(events, home, away, game_id, slug)
