"""Tests for the end-to-end fair-value engine."""

from __future__ import annotations

import math

from fvmatch.engine import analyze_match


def test_model_only_probs_sum_to_one() -> None:
    a = analyze_match("Portugal", "Uzbekistan")
    total = a.p_home + a.p_draw + a.p_away
    assert math.isclose(total, 1.0, abs_tol=1e-9)
    assert a.p_home > a.p_away  # Portugal stronger
    # No odds → no bets, no edge
    assert a.overround is None
    assert not a.has_bets
    assert all(o.edge is None for o in a.outcomes)


def test_favorite_positive_edge_produces_bet() -> None:
    # Market underprices the favourite relative to the model → a bet appears.
    a = analyze_match(
        "Portugal",
        "Uzbekistan",
        home_odds=1.45,
        draw_odds=5.0,
        away_odds=8.0,
    )
    assert a.overround is not None and a.overround > 0
    home = next(o for o in a.outcomes if o.outcome == "home")
    assert home.edge is not None and home.edge > 0
    assert home.bet is True
    assert home.stake_usd > 0
    # Total staked never exceeds the per-match cap fraction of bankroll
    total = sum(o.stake_usd for o in a.outcomes)
    assert total <= 0.05 * 1000.0 + 1e-6


def test_efficient_market_no_bet() -> None:
    # Odds set close to the model's own fair odds → edge below threshold.
    base = analyze_match("Portugal", "Uzbekistan")
    fair_home = 1.0 / base.p_home
    fair_draw = 1.0 / base.p_draw
    fair_away = 1.0 / base.p_away
    a = analyze_match(
        "Portugal",
        "Uzbekistan",
        home_odds=fair_home,
        draw_odds=fair_draw,
        away_odds=fair_away,
    )
    assert not a.has_bets


def test_home_advantage_shifts_probs() -> None:
    neutral = analyze_match("Portugal", "Uzbekistan", neutral=True)
    home_field = analyze_match("Portugal", "Uzbekistan", neutral=False)
    assert home_field.p_home > neutral.p_home


def test_elo_override() -> None:
    a = analyze_match("TeamA", "TeamB", elo_home=2000, elo_away=1500)
    assert a.elo_home == 2000
    assert a.p_home > a.p_away
