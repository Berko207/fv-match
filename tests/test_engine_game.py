"""Tests for the whole-game engine: pricing + global gating + JSON output."""

from __future__ import annotations

import json

from fvmatch.config import settings
from fvmatch.data.polymarket.game import build_surface
from fvmatch.engine_game import analyze_game
from tests.test_game_surface import CORNERS_EVENT, MAIN_EVENT

UNKNOWN_EVENT = {
    "id": 352001,
    "title": "Czechia vs. Mexico",
    "gameId": 90086955,
    "markets": [
        {
            "question": "Will there be a red card in the match?",
            "outcomes": json.dumps(["Yes", "No"]),
            "outcomePrices": json.dumps(["0.3", "0.7"]),
            "clobTokenIds": json.dumps(["t-y", "t-n"]),
            "conditionId": "0x99",
            "closed": False,
            "liquidityNum": 8000.0,
        }
    ],
}


def _surface():
    return build_surface(
        [MAIN_EVENT, CORNERS_EVENT, UNKNOWN_EVENT],
        "Czechia",
        "Mexico",
        90086955,
        "fifwc-cze-mex-2026-06-24",
    )


def test_analyze_game_prices_and_proposes() -> None:
    ga = analyze_game(_surface(), neutral=True)
    assert ga.n_markets >= 5
    assert ga.proposed_bets  # there are +EV legs against these prices
    # 1X2 edges reproduce the single-match result (sanity anchor)
    one_x_two = next(m for m in ga.markets if m.market_type == "1x2")
    home = next(o for o in one_x_two.outcomes if o.key == "home")
    assert home.model_p is not None and abs(home.model_p - 0.283) < 0.01


def test_game_exposure_cap_respected() -> None:
    ga = analyze_game(_surface(), neutral=True)
    cap_usd = settings.kelly_cap * settings.bankroll
    assert ga.total_stake_usd <= cap_usd + 1e-6


def test_proposed_bets_sorted_by_ev() -> None:
    ga = analyze_game(_surface(), neutral=True)
    evs = [b.ev_per_dollar for b in ga.proposed_bets]
    assert evs == sorted(evs, reverse=True)


def test_prior_based_flagged_on_corners() -> None:
    ga = analyze_game(_surface(), neutral=True)
    corners = [b for b in ga.proposed_bets if b.market_type == "total_corners"]
    assert corners and all(b.prior_based for b in corners)


def test_unknown_market_carried_but_unpriced() -> None:
    ga = analyze_game(_surface(), neutral=True)
    unknown = [m for m in ga.markets if m.market_type == "unknown"]
    assert unknown, "unpriceable markets must still appear as read-only signals"
    assert all(not m.priceable for m in unknown)
    assert all(not m.has_bet for m in unknown)


def test_to_dict_is_json_serializable() -> None:
    ga = analyze_game(_surface(), neutral=True)
    blob = json.dumps(ga.to_dict())  # must not raise
    restored = json.loads(blob)
    assert restored["home"] == "Czechia"
    assert "proposed_bets" in restored and "markets" in restored


def test_dry_run_default_true() -> None:
    ga = analyze_game(_surface(), neutral=True)
    assert ga.dry_run is True
