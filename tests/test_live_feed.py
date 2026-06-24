"""Deterministic tests for the ESPN live match-state parser (no network)."""

from __future__ import annotations

from fvmatch.data.live_feed import LiveMatch, parse_scoreboard_event


def _event(
    *,
    state: str = "in",
    clock: float | None = 3780.0,
    detail: str = "63'",
    home_score: str = "1",
    away_score: str = "0",
) -> dict:
    """Build a minimal ESPN scoreboard event mirroring the real payload shape."""
    return {
        "id": "760459",
        "name": "Congo DR at Colombia",
        "competitions": [
            {
                "status": {
                    "clock": clock,
                    "displayClock": detail,
                    "period": 2,
                    "type": {
                        "state": state,
                        "name": "STATUS_SECOND_HALF",
                        "detail": detail,
                        "shortDetail": detail,
                        "completed": state == "post",
                    },
                },
                "competitors": [
                    {
                        "homeAway": "home",
                        "score": home_score,
                        "team": {"id": "203", "displayName": "Colombia"},
                    },
                    {
                        "homeAway": "away",
                        "score": away_score,
                        "team": {"id": "21204", "displayName": "Congo DR"},
                    },
                ],
            }
        ],
    }


def test_parse_scoreboard_event_basic() -> None:
    match = parse_scoreboard_event(_event())
    assert match is not None
    assert match.event_id == "760459"
    assert match.home == "Colombia"
    assert match.away == "Congo DR"
    assert match.home_goals == 1
    assert match.away_goals == 0
    assert match.minute == 63.0  # clock 3780s / 60
    assert match.status_state == "in"
    assert match.is_live
    assert match.home_team_id == "203"
    assert match.away_team_id == "21204"


def test_minute_from_clock_states() -> None:
    # Halftime: clock capped at 2700s -> 45'.
    ht = parse_scoreboard_event(_event(state="in", clock=2700.0, detail="HT"))
    assert ht is not None and ht.minute == 45.0
    # Finished -> full match length, regardless of clock.
    ft = parse_scoreboard_event(_event(state="post", clock=None, detail="FT"))
    assert ft is not None and ft.minute == 90.0 and ft.is_final
    # Pre-match -> 0'.
    pre = parse_scoreboard_event(_event(state="pre", clock=None, detail="Sat"))
    assert pre is not None and pre.minute == 0.0 and pre.is_pre


def test_minute_falls_back_to_detail_digits() -> None:
    # No numeric clock, but a "63'" style detail string.
    match = parse_scoreboard_event(_event(state="in", clock=None, detail="63'"))
    assert match is not None and match.minute == 63.0


def test_oriented_to_same_order_keeps_goals() -> None:
    # "Congo DR" (ESPN) <-> "DR Congo" (Polymarket) match by token overlap.
    match = parse_scoreboard_event(_event()).oriented_to("Colombia", "DR Congo")
    assert match is not None
    assert match.home == "Colombia" and match.away == "DR Congo"
    assert (match.home_goals, match.away_goals) == (1, 0)


def test_oriented_to_swapped_order_swaps_goals_and_ids() -> None:
    match = parse_scoreboard_event(_event()).oriented_to("DR Congo", "Colombia")
    assert match is not None
    assert match.home == "DR Congo" and match.away == "Colombia"
    # Colombia (ESPN home, 1 goal) is now the away side.
    assert (match.home_goals, match.away_goals) == (0, 1)
    assert match.home_team_id == "21204" and match.away_team_id == "203"


def test_oriented_to_wrong_fixture_returns_none() -> None:
    assert parse_scoreboard_event(_event()).oriented_to("France", "Spain") is None


def test_to_live_state_maps_fields() -> None:
    match = parse_scoreboard_event(_event(home_score="2", away_score="1"))
    assert match is not None
    state = match.to_live_state()
    assert state.minute == 63.0
    assert state.home_goals == 2
    assert state.away_goals == 1
    assert state.match_length == 90.0


def test_missing_competitors_returns_none() -> None:
    assert (
        parse_scoreboard_event({"id": "x", "competitions": [{"competitors": []}]})
        is None
    )
    assert parse_scoreboard_event({"id": "x"}) is None


def test_status_at_event_level_is_used() -> None:
    # Some payloads carry status on the event, not the competition.
    event = _event()
    event["status"] = event["competitions"][0].pop("status")
    match = parse_scoreboard_event(event)
    assert match is not None and match.minute == 63.0 and match.status_state == "in"


def test_returns_livematch_type() -> None:
    assert isinstance(parse_scoreboard_event(_event()), LiveMatch)
