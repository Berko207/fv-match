"""Tests for full-surface parsing (event dicts -> MarketSurface).

The event payloads mirror the REAL captured CZE-MEX shapes: outcome/price/token
arrays are JSON-encoded strings, and win legs carry the ISO date in the question.
"""

from __future__ import annotations

import json

from fvmatch.data.polymarket.game import build_surface, event_to_lines
from fvmatch.data.polymarket.taxonomy import MarketType


def _mkt(question, outcomes, prices, cond, tokens=None, liq=10000.0):
    return {
        "question": question,
        "outcomes": json.dumps(outcomes),
        "outcomePrices": json.dumps([str(p) for p in prices]),
        "clobTokenIds": json.dumps(tokens or ["t-yes", "t-no"]),
        "conditionId": cond,
        "closed": False,
        "liquidityNum": liq,
    }


MAIN_EVENT = {
    "id": 351767,
    "title": "Czechia vs. Mexico",
    "gameId": 90086955,
    "markets": [
        _mkt("Will Czechia win on 2026-06-24?", ["Yes", "No"], [0.215, 0.785], "0xa"),
        _mkt(
            "Will Czechia vs. Mexico end in a draw?",
            ["Yes", "No"],
            [0.225, 0.775],
            "0xb",
        ),
        _mkt("Will Mexico win on 2026-06-24?", ["Yes", "No"], [0.555, 0.445], "0xc"),
    ],
}

CORNERS_EVENT = {
    "id": 351999,
    "title": "Czechia vs. Mexico",
    "gameId": 90086955,
    "markets": [
        _mkt("Total Corners Over 8.5?", ["Over", "Under"], [0.52, 0.48], "0xd"),
        _mkt("Total goals Over/Under 2.5", ["Over", "Under"], [0.46, 0.54], "0xe"),
        _mkt(
            "Mexico Total Goals Over 1.5", ["Over", "Under"], [0.6, 0.4], "0xf"
        ),
    ],
}


def test_moneyline_assembled_from_three_legs() -> None:
    lines = event_to_lines(MAIN_EVENT, "Czechia", "Mexico")
    assert len(lines) == 1
    ml = lines[0]
    assert ml.market_type is MarketType.ONE_X_TWO
    keys = {o.key: o for o in ml.outcomes}
    assert set(keys) == {"home", "draw", "away"}
    # Mexico is away; its 'Yes' price 0.555 becomes the away leg price
    assert abs(keys["away"].price - 0.555) < 1e-9
    assert abs(keys["home"].price - 0.215) < 1e-9


def test_date_in_win_question_not_exact_score() -> None:
    lines = event_to_lines(MAIN_EVENT, "Czechia", "Mexico")
    assert all(line.market_type is not MarketType.EXACT_SCORE for line in lines)


def test_corner_market_not_swallowed_by_moneyline() -> None:
    lines = event_to_lines(CORNERS_EVENT, "Czechia", "Mexico")
    types = {line.market_type for line in lines}
    # No moneyline should be assembled from a corners/totals event
    assert MarketType.ONE_X_TWO not in types
    assert MarketType.TOTAL_CORNERS in types
    assert MarketType.TOTAL_GOALS in types
    assert MarketType.TEAM_TOTAL_GOALS in types


def test_build_surface_combines_and_dedupes() -> None:
    surface = build_surface(
        [MAIN_EVENT, CORNERS_EVENT, MAIN_EVENT],  # duplicate main on purpose
        "Czechia",
        "Mexico",
        90086955,
        "fifwc-cze-mex-2026-06-24",
    )
    types = [line.market_type for line in surface.lines]
    assert types.count(MarketType.ONE_X_TWO) == 1  # deduped
    assert MarketType.TOTAL_CORNERS in types
    assert len(surface.priceable()) >= 3


def test_token_ids_carried_for_execution() -> None:
    lines = event_to_lines(CORNERS_EVENT, "Czechia", "Mexico")
    corners = next(line for line in lines if line.market_type is MarketType.TOTAL_CORNERS)
    assert all(o.token_id for o in corners.outcomes)
