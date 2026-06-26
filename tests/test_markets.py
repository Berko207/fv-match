"""Tests for goals-derived market pricers (sums over the scoreline grid)."""

from __future__ import annotations

import math

import numpy as np

from fvmatch.model.dixon_coles import marginal_hda, scoreline_matrix
from fvmatch.model.markets import (
    first_half_matrix,
    goal_difference_pmf,
    prob_both_teams_to_score,
    prob_clean_sheet,
    prob_double_chance,
    prob_draw_no_bet,
    prob_exact_score,
    prob_hda,
    prob_odd_even_total,
    prob_team_total_over,
    prob_total_over,
    prob_total_over_under,
    prob_winning_margin,
    total_goals_pmf,
)


def _matrix() -> np.ndarray:
    return scoreline_matrix(1.7, 1.1, rho=-0.08, max_goals=10)


def test_total_goals_pmf_sums_to_one() -> None:
    pmf = total_goals_pmf(_matrix())
    assert math.isclose(float(pmf.sum()), 1.0, abs_tol=1e-9)
    assert (pmf >= 0).all()


def test_goal_difference_pmf_consistent_with_hda() -> None:
    m = _matrix()
    pmf, offset = goal_difference_pmf(m)
    assert math.isclose(float(pmf.sum()), 1.0, abs_tol=1e-9)
    # P(diff == 0) must equal the draw probability
    p_home, p_draw, p_away = marginal_hda(m)
    assert math.isclose(float(pmf[offset]), p_draw, abs_tol=1e-12)
    # Positive differences are home wins, negative are away wins
    pos = float(pmf[offset + 1 :].sum())
    neg = float(pmf[:offset].sum())
    assert math.isclose(pos, p_home, abs_tol=1e-12)
    assert math.isclose(neg, p_away, abs_tol=1e-12)


def test_prob_hda_matches_dixon_coles() -> None:
    m = _matrix()
    assert prob_hda(m) == marginal_hda(m)


def test_double_chance_and_dc_partition() -> None:
    m = _matrix()
    h, d, a = prob_hda(m)
    dc = prob_double_chance(m)
    assert math.isclose(dc["1X"], h + d, abs_tol=1e-12)
    assert math.isclose(dc["12"], h + a, abs_tol=1e-12)
    assert math.isclose(dc["X2"], d + a, abs_tol=1e-12)


def test_draw_no_bet_conditions_out_the_draw() -> None:
    m = _matrix()
    h, _, a = prob_hda(m)
    dnb = prob_draw_no_bet(m)
    assert math.isclose(dnb["home"] + dnb["away"], 1.0, abs_tol=1e-9)
    assert math.isclose(dnb["home"], h / (h + a), abs_tol=1e-12)


def test_total_over_under_complement_and_monotone() -> None:
    m = _matrix()
    ou = prob_total_over_under(m, 2.5)
    assert math.isclose(ou["over"] + ou["under"], 1.0, abs_tol=1e-9)
    # Over a higher line is strictly less likely
    assert prob_total_over(m, 3.5) < prob_total_over(m, 2.5)
    assert prob_total_over(m, 1.5) > prob_total_over(m, 2.5)


def test_btts_against_brute_force() -> None:
    m = _matrix()
    rows, cols = m.shape
    brute = sum(
        float(m[i, j]) for i in range(1, rows) for j in range(1, cols)
    )
    assert math.isclose(prob_both_teams_to_score(m)["yes"], brute, abs_tol=1e-9)


def test_team_total_over_uses_correct_marginal() -> None:
    m = scoreline_matrix(2.4, 0.6)  # strong home
    # Home is far likelier to exceed 1.5 goals than away
    assert prob_team_total_over(m, 1.5, "home") > prob_team_total_over(
        m, 1.5, "away"
    )


def test_clean_sheet_complement() -> None:
    m = _matrix()
    cs = prob_clean_sheet(m, "home")
    assert math.isclose(cs["yes"] + cs["no"], 1.0, abs_tol=1e-9)
    # Home clean sheet == away scores zero == sum of column 0
    assert math.isclose(cs["yes"], float(m[:, 0].sum()), abs_tol=1e-12)


def test_exact_score_matches_cell_and_clamps_tail() -> None:
    m = _matrix()
    assert prob_exact_score(m, 1, 1) == float(m[1, 1])
    assert prob_exact_score(m, 99, 99) == 0.0


def test_winning_margin_partition() -> None:
    m = _matrix()
    pmf, _ = goal_difference_pmf(m)
    # Summing every home margin + every away margin + draw == 1
    max_margin = m.shape[0] - 1
    total = float(np.trace(m))  # draw (margin 0)
    for margin in range(1, max_margin + 1):
        total += prob_winning_margin(m, margin, "home")
        total += prob_winning_margin(m, margin, "away")
    assert math.isclose(total, 1.0, abs_tol=1e-9)


def test_odd_even_complement() -> None:
    oe = prob_odd_even_total(_matrix())
    assert math.isclose(oe["odd"] + oe["even"], 1.0, abs_tol=1e-9)


def test_first_half_has_fewer_goals_than_full_match() -> None:
    full = scoreline_matrix(1.8, 1.2)
    half = first_half_matrix(1.8, 1.2, first_half_goal_share=0.45)
    # Expected first-half goals < expected full-match goals
    full_exp = float((total_goals_pmf(full) * np.arange(len(total_goals_pmf(full)))).sum())
    half_exp = float((total_goals_pmf(half) * np.arange(len(total_goals_pmf(half)))).sum())
    assert half_exp < full_exp
    assert math.isclose(float(half.sum()), 1.0, abs_tol=1e-9)
