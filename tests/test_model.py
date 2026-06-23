"""Tests for the Dixon-Coles model and Elo prior."""

from __future__ import annotations

import math

import numpy as np

from fvmatch.model.dixon_coles import (
    fit,
    lambdas_from_elo,
    marginal_hda,
    predict_scoreline_matrix,
    scoreline_matrix,
)


def test_scoreline_matrix_normalized() -> None:
    m = scoreline_matrix(1.6, 1.1, rho=-0.08, max_goals=10)
    assert m.shape == (11, 11)
    assert math.isclose(float(m.sum()), 1.0, abs_tol=1e-9)
    assert (m >= 0).all()


def test_marginal_hda_sums_to_one() -> None:
    m = scoreline_matrix(1.5, 1.2)
    p_home, p_draw, p_away = marginal_hda(m)
    assert math.isclose(p_home + p_draw + p_away, 1.0, abs_tol=1e-9)
    assert all(0.0 <= p <= 1.0 for p in (p_home, p_draw, p_away))


def test_stronger_team_more_likely() -> None:
    m = scoreline_matrix(2.3, 0.4)
    p_home, _, p_away = marginal_hda(m)
    assert p_home > p_away


def test_lambdas_from_elo_supremacy() -> None:
    # Equal Elo, neutral → equal lambdas summing ~ base_goals
    lh, la = lambdas_from_elo(1800, 1800, home_advantage=0.0, base_goals=2.6)
    assert math.isclose(lh, la, abs_tol=1e-9)
    assert math.isclose(lh + la, 2.6, abs_tol=1e-9)
    # Stronger home → bigger home lambda
    lh2, la2 = lambdas_from_elo(2030, 1740, home_advantage=0.0)
    assert lh2 > la2
    assert lh2 > lh


def test_lambdas_floor_on_mismatch() -> None:
    lh, la = lambdas_from_elo(2200, 1000, home_advantage=0.0, goal_scale=150.0)
    assert la >= 0.0
    assert lh > la


def test_fit_recovers_stronger_team() -> None:
    # Synthetic league: 'Strong' routinely beats 'Weak'; 'Mid' in between.
    fixtures = []
    for _ in range(8):
        fixtures.append(
            {
                "home_team": "Strong",
                "away_team": "Weak",
                "home_goals": 4,
                "away_goals": 0,
            }
        )
        fixtures.append(
            {
                "home_team": "Weak",
                "away_team": "Strong",
                "home_goals": 0,
                "away_goals": 3,
            }
        )
        fixtures.append(
            {
                "home_team": "Strong",
                "away_team": "Mid",
                "home_goals": 2,
                "away_goals": 1,
            }
        )
        fixtures.append(
            {"home_team": "Mid", "away_team": "Weak", "home_goals": 2, "away_goals": 0}
        )
    params = fit(fixtures, rho=-0.05)
    assert params["model"] == "dixon_coles"
    assert set(params["teams"]) == {"Strong", "Mid", "Weak"}
    # Attack ranking: Strong > Mid > Weak
    assert params["attack"]["Strong"] > params["attack"]["Weak"]

    m = predict_scoreline_matrix("Strong", "Weak", params, max_goals=8)
    p_home, _, p_away = marginal_hda(m)
    assert p_home > p_away


def test_predict_unknown_team_falls_back() -> None:
    params = {
        "attack": {"A": 0.3},
        "defence": {"A": -0.1},
        "mu": math.log(1.3),
        "gamma": 0.2,
        "rho": -0.08,
        "home_advantage": True,
    }
    m = predict_scoreline_matrix("A", "Unknown", params)
    assert math.isclose(float(np.sum(m)), 1.0, abs_tol=1e-9)
