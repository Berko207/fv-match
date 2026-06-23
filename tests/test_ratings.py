"""Tests for the Elo ratings prior."""

from __future__ import annotations

import math

from fvmatch.model.ratings_prior import (
    DEFAULT_ELO,
    elo_update,
    expected_score,
    get_rating,
    load_seed_ratings,
)


def test_seed_loads_known_teams() -> None:
    ratings = load_seed_ratings()
    assert "Portugal" in ratings
    assert "Uzbekistan" in ratings
    assert ratings["Portugal"] > ratings["Uzbekistan"]


def test_get_rating_case_insensitive_and_default() -> None:
    assert get_rating("portugal") == get_rating("Portugal")
    assert get_rating("Nowhere FC United") == DEFAULT_ELO
    assert get_rating("X", ratings={"X": 1900.0}) == 1900.0


def test_expected_score_symmetry() -> None:
    assert math.isclose(expected_score(1800, 1800), 0.5, abs_tol=1e-9)
    a = expected_score(2000, 1700)
    b = expected_score(1700, 2000)
    assert math.isclose(a + b, 1.0, abs_tol=1e-9)
    assert a > 0.5


def test_elo_update_zero_sum_and_direction() -> None:
    new_a, new_b = elo_update(1800, 1800, score_a=1.0, k=30.0)
    # Winner gains exactly what loser drops
    assert math.isclose((new_a - 1800) + (new_b - 1800), 0.0, abs_tol=1e-9)
    assert new_a > 1800 > new_b


def test_elo_update_blowout_multiplier() -> None:
    _, _ = elo_update(1800, 1800, 1.0, goal_diff=1)
    big_a, _ = elo_update(1800, 1800, 1.0, goal_diff=4)
    small_a, _ = elo_update(1800, 1800, 1.0, goal_diff=1)
    assert big_a > small_a
