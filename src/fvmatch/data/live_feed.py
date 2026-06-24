"""Best-effort live match-state feed from ESPN's public scoreboard.

No API key required. Polls the free ESPN soccer scoreboard for a league
(default FIFA World Cup, ``fifa.world``) and parses an in-progress fixture into
a :class:`LiveMatch` snapshot — current score, elapsed minute, status, and red
cards — which maps directly onto :class:`fvmatch.model.live.LiveState`.

Like :mod:`fvmatch.data.polymarket`, this is a convenience ingestion layer: it
degrades gracefully (returns ``None`` / empty) on any network or parse error and
never raises into the analysis path. The pure parsing helpers
(:func:`parse_scoreboard_event`, :meth:`LiveMatch.oriented_to`) take plain dicts
so they are unit-testable without the network.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Any

import httpx

from fvmatch.model.live import LiveState

ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard"
ESPN_SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/summary"
DEFAULT_LEAGUE = "fifa.world"  # FIFA World Cup
_TIMEOUT = 15.0
_MATCH_LENGTH = 90.0


@dataclass(frozen=True)
class LiveMatch:
    """Parsed live snapshot of an ESPN soccer fixture (canonical orientation).

    ``home`` / ``away`` and the goal counts are oriented to the names the caller
    matched on (see :meth:`oriented_to`), so they stay consistent with the
    Polymarket market and the Elo prior regardless of ESPN's home/away flag.
    """

    event_id: str
    home: str
    away: str
    home_goals: int
    away_goals: int
    minute: float
    status_state: str  # "pre" | "in" | "post"
    status_detail: str  # e.g. "HT", "63'", "FT"
    status_name: str = ""  # e.g. "STATUS_SECOND_HALF"
    home_team_id: str = ""
    away_team_id: str = ""
    red_cards_home: int = 0
    red_cards_away: int = 0

    @property
    def is_live(self) -> bool:
        return self.status_state == "in"

    @property
    def is_final(self) -> bool:
        return self.status_state == "post"

    @property
    def is_pre(self) -> bool:
        return self.status_state == "pre"

    def to_live_state(self) -> LiveState:
        """Map this snapshot onto the in-play model's :class:`LiveState`."""
        return LiveState(
            minute=self.minute,
            home_goals=self.home_goals,
            away_goals=self.away_goals,
            red_cards_home=self.red_cards_home,
            red_cards_away=self.red_cards_away,
            match_length=_MATCH_LENGTH,
        )

    def oriented_to(self, home_name: str, away_name: str) -> LiveMatch | None:
        """Return this match re-labelled to ``home_name``/``away_name``.

        Matches each requested name against the two ESPN competitors by token
        overlap. Returns a copy oriented so ``home`` is ``home_name`` (swapping
        goals/reds/ids if ESPN listed the teams the other way round), or ``None``
        if this event is not the requested fixture.
        """
        want_home, want_away = _name_tokens(home_name), _name_tokens(away_name)
        have_home, have_away = _name_tokens(self.home), _name_tokens(self.away)
        if _tokens_match(want_home, have_home) and _tokens_match(want_away, have_away):
            return replace(self, home=home_name, away=away_name)
        if _tokens_match(want_home, have_away) and _tokens_match(want_away, have_home):
            return replace(
                self,
                home=home_name,
                away=away_name,
                home_goals=self.away_goals,
                away_goals=self.home_goals,
                red_cards_home=self.red_cards_away,
                red_cards_away=self.red_cards_home,
                home_team_id=self.away_team_id,
                away_team_id=self.home_team_id,
            )
        return None


def _name_tokens(name: str) -> set[str]:
    """Lowercase alphanumeric tokens of a team name, minus noise words."""
    tokens = set(re.findall(r"[a-z0-9]+", name.lower()))
    return tokens - {"vs", "fc", "afc", "national", "team"}


def _tokens_match(a: set[str], b: set[str]) -> bool:
    """True if either token set is a (non-empty) subset of the other."""
    return bool(a) and bool(b) and (a <= b or b <= a)


def _coerce_int(value: Any) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def _team_name(competitor: dict[str, Any]) -> str:
    team = competitor.get("team") or {}
    return str(team.get("displayName") or team.get("name") or team.get("shortDisplayName") or "")


def _minute_from_status(status: dict[str, Any], state: str) -> float:
    """Elapsed match minutes from an ESPN status block, clamped to [0, 90]."""
    if state == "pre":
        return 0.0
    if state == "post":
        return _MATCH_LENGTH
    clock = status.get("clock")
    if clock is not None:
        try:
            return min(max(float(clock) / 60.0, 0.0), _MATCH_LENGTH)
        except (TypeError, ValueError):
            pass
    # Fallback: leading digits of a display string like "63'" or "45'+2'".
    detail = str((status.get("type") or {}).get("detail") or status.get("displayClock") or "")
    m = re.match(r"\s*(\d+)", detail)
    if m:
        return min(max(float(m.group(1)), 0.0), _MATCH_LENGTH)
    return 0.0


def parse_scoreboard_event(event: dict[str, Any]) -> LiveMatch | None:
    """Parse one ESPN scoreboard ``event`` dict into a :class:`LiveMatch`.

    Oriented by ESPN's own home/away flag (use :meth:`LiveMatch.oriented_to` to
    re-label to canonical names). Returns ``None`` if the event lacks two
    competitors. Red-card counts default to 0 (filled in by network lookups).
    """
    comps = event.get("competitions") or []
    if not comps:
        return None
    comp = comps[0]
    status = comp.get("status") or event.get("status") or {}
    stype = status.get("type") or {}
    state = str(stype.get("state") or "")
    detail = str(stype.get("detail") or stype.get("shortDetail") or "")
    name = str(stype.get("name") or "")
    minute = _minute_from_status(status, state)

    competitors = comp.get("competitors") or []
    home_c = next((c for c in competitors if c.get("homeAway") == "home"), None)
    away_c = next((c for c in competitors if c.get("homeAway") == "away"), None)
    if (home_c is None or away_c is None) and len(competitors) == 2:
        home_c, away_c = competitors[0], competitors[1]
    if home_c is None or away_c is None:
        return None

    return LiveMatch(
        event_id=str(event.get("id") or ""),
        home=_team_name(home_c),
        away=_team_name(away_c),
        home_goals=_coerce_int(home_c.get("score")),
        away_goals=_coerce_int(away_c.get("score")),
        minute=minute,
        status_state=state,
        status_detail=detail,
        status_name=name,
        home_team_id=str((home_c.get("team") or {}).get("id") or ""),
        away_team_id=str((away_c.get("team") or {}).get("id") or ""),
    )


def _fetch_events(league: str) -> list[dict[str, Any]]:
    try:
        resp = httpx.get(ESPN_SCOREBOARD.format(league=league), timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except (httpx.HTTPError, ValueError):
        return []
    events = data.get("events") if isinstance(data, dict) else None
    return events if isinstance(events, list) else []


def _fetch_red_cards(
    league: str, event_id: str, home_team_id: str, away_team_id: str
) -> tuple[int, int]:
    """Count red cards per side from the ESPN summary ``keyEvents`` (best-effort)."""
    if not event_id:
        return (0, 0)
    try:
        resp = httpx.get(
            ESPN_SUMMARY.format(league=league),
            params={"event": event_id},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except (httpx.HTTPError, ValueError):
        return (0, 0)
    key_events = data.get("keyEvents") if isinstance(data, dict) else None
    if not isinstance(key_events, list):
        return (0, 0)
    home = away = 0
    for ke in key_events:
        if not isinstance(ke, dict):
            continue
        text = str((ke.get("type") or {}).get("text") or "").lower()
        if "red card" not in text:
            continue
        tid = str((ke.get("team") or {}).get("id") or "")
        if tid and tid == home_team_id:
            home += 1
        elif tid and tid == away_team_id:
            away += 1
    return (home, away)


def find_live_match(
    home_name: str,
    away_name: str,
    league: str = DEFAULT_LEAGUE,
    *,
    fetch_cards: bool = True,
) -> LiveMatch | None:
    """Find the ESPN fixture for ``home_name`` vs ``away_name`` in ``league``.

    Returns a :class:`LiveMatch` oriented to the requested names, with red cards
    filled in from the summary endpoint when the match is in play or finished.
    ``None`` if the fixture is not on the scoreboard or the feed is unreachable.
    """
    for event in _fetch_events(league):
        parsed = parse_scoreboard_event(event)
        if parsed is None:
            continue
        match = parsed.oriented_to(home_name, away_name)
        if match is None:
            continue
        if fetch_cards and match.status_state in ("in", "post"):
            rh, ra = _fetch_red_cards(
                league, match.event_id, match.home_team_id, match.away_team_id
            )
            match = replace(match, red_cards_home=rh, red_cards_away=ra)
        return match
    return None
