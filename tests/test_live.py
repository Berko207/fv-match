"""Deterministic tests for the in-play conditional scoreline model."""

from __future__ import annotations

import math

import numpy as np
import pytest

from fvmatch.engine import analyze_live_match
from fvmatch.model.dixon_coles import lambdas_from_elo, marginal_hda, scoreline_matrix
from fvmatch.model.live import (
    LiveState,
    conditional_scoreline_matrix,
    live_hda,
)


def _fixture_lambdas() -> tuple[float, float]:
    return lambdas_from_elo(1850.0, 1650.0, home_advantage=0.0)


def test_kickoff_matches_prematch_matrix() -> None:
    lam_home, lam_away = _fixture_lambdas()
    rho = -0.08
    prematch = scoreline_matrix(lam_home, lam_away, rho=rho, max_goals=10)
    state = LiveState(minute=0.0, home_goals=0, away_goals=0)
    live = conditional_scoreline_matrix(
        lam_home, lam_away, state, rho=rho, max_goals=10, intensity_profile="uniform"
    )
    assert np.allclose(live, prematch, atol=1e-12)

    p_pre = marginal_hda(prematch)
    p_live = live_hda(lam_home, lam_away, state, rho=rho, intensity_profile="uniform")
    assert p_live == pytest.approx(p_pre, abs=1e-12)


def test_late_lead_home_dominates() -> None:
    lam_home, lam_away = _fixture_lambdas()
    prematch = marginal_hda(
        scoreline_matrix(lam_home, lam_away, rho=-0.08, max_goals=10)
    )
    state = LiveState(minute=80.0, home_goals=1, away_goals=0)
    p_home, p_draw, p_away = live_hda(
        lam_home, lam_away, state, rho=-0.08, intensity_profile="rising"
    )
    assert p_home > prematch[0] + 0.15
    assert p_away < prematch[2] * 0.5
    assert p_home + p_draw + p_away == pytest.approx(1.0, abs=1e-9)


def test_full_time_point_mass() -> None:
    lam_home, lam_away = _fixture_lambdas()
    for hg, ag, expected in ((0, 0, "draw"), (1, 0, "home"), (0, 2, "away")):
        state = LiveState(minute=90.0, home_goals=hg, away_goals=ag)
        matrix = conditional_scoreline_matrix(lam_home, lam_away, state)
        assert matrix.sum() == pytest.approx(1.0, abs=1e-12)
        assert matrix[hg, ag] == pytest.approx(1.0, abs=1e-12)
        p_home, p_draw, p_away = live_hda(lam_home, lam_away, state)
        if expected == "home":
            assert p_home == pytest.approx(1.0)
        elif expected == "draw":
            assert p_draw == pytest.approx(1.0)
        else:
            assert p_away == pytest.approx(1.0)


def test_matrix_invariants_no_nans() -> None:
    lam_home, lam_away = _fixture_lambdas()
    for minute in (0.0, 45.0, 89.5, 90.0, 95.0, -5.0):
        state = LiveState(minute=minute, home_goals=0, away_goals=0)
        matrix = conditional_scoreline_matrix(lam_home, lam_away, state)
        assert not np.any(np.isnan(matrix))
        assert matrix.sum() == pytest.approx(1.0, abs=1e-9)
        assert (matrix >= 0).all()


def test_red_card_away_boosts_home_remaining_rate() -> None:
    lam_home, lam_away = _fixture_lambdas()
    base = LiveState(minute=60.0, home_goals=0, away_goals=0)
    with_red = LiveState(minute=60.0, home_goals=0, away_goals=0, red_cards_away=1)
    p_base = live_hda(lam_home, lam_away, base, intensity_profile="uniform")
    p_red = live_hda(lam_home, lam_away, with_red, intensity_profile="uniform")
    assert p_red[0] > p_base[0]
    assert p_red[2] < p_base[2]


def test_rising_more_remaining_goals_than_uniform() -> None:
    lam_home, lam_away = _fixture_lambdas()
    state = LiveState(minute=70.0, home_goals=0, away_goals=0)
    p_uniform = live_hda(lam_home, lam_away, state, intensity_profile="uniform")
    p_rising = live_hda(lam_home, lam_away, state, intensity_profile="rising")
    # More remaining goal mass → lower draw share at 0-0.
    assert p_rising[1] < p_uniform[1]
    assert p_rising[0] + p_rising[2] > p_uniform[0] + p_uniform[2]


def test_analyze_live_match_engine_wiring() -> None:
    state = LiveState(minute=75.0, home_goals=1, away_goals=1)
    a = analyze_live_match("Portugal", "Uzbekistan", state)
    total = a.p_home + a.p_draw + a.p_away
    assert math.isclose(total, 1.0, abs_tol=1e-9)
    assert a.live_state == state
    assert a.top_scorelines
    assert all(i >= 1 or j >= 1 for i, j, _ in a.top_scorelines)
