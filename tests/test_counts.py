"""Tests for the prior-based Poisson count models (corners/shots/assists)."""

from __future__ import annotations

import math

from fvmatch.model.counts import (
    assist_lambdas,
    count_lambdas,
    half_rate,
    poisson_pmf,
    poisson_sf,
    prob_count_over,
    prob_count_over_under,
    total_rate,
)


def test_count_lambdas_split_sums_to_base() -> None:
    lh, la = count_lambdas(1800, 1800, 10.5, scale=500.0)
    assert math.isclose(lh + la, 10.5, abs_tol=1e-9)
    assert math.isclose(lh, la, abs_tol=1e-9)  # equal Elo → even split


def test_count_lambdas_stronger_side_gets_more() -> None:
    lh, la = count_lambdas(1900, 1700, 10.5, scale=500.0)
    assert lh > la
    assert math.isclose(lh + la, 10.5, abs_tol=1e-9)


def test_count_lambdas_floor() -> None:
    # Absurd supremacy must not drive a side negative
    lh, la = count_lambdas(3000, 1000, 4.0, scale=50.0)
    assert la >= 0.0


def test_assist_lambdas_scale_goals() -> None:
    ah, aa = assist_lambdas(1.8, 1.0, assist_rate=0.77)
    assert math.isclose(ah, 1.8 * 0.77, abs_tol=1e-9)
    assert math.isclose(aa, 1.0 * 0.77, abs_tol=1e-9)


def test_poisson_pmf_normalizes() -> None:
    lam = 9.5
    mass = sum(poisson_pmf(lam, k) for k in range(60))
    assert math.isclose(mass, 1.0, abs_tol=1e-9)


def test_poisson_sf_complements_cdf() -> None:
    lam = 5.0
    # P(N>=0) == 1
    assert math.isclose(poisson_sf(lam, 0), 1.0, abs_tol=1e-12)
    # P(N>=k) + P(N<k) == 1
    k = 4
    below = sum(poisson_pmf(lam, i) for i in range(k))
    assert math.isclose(poisson_sf(lam, k) + below, 1.0, abs_tol=1e-9)


def test_prob_count_over_halfline() -> None:
    lam = 10.5
    # Over 8.5 == P(N >= 9)
    assert math.isclose(
        prob_count_over(lam, 8.5), poisson_sf(lam, 9), abs_tol=1e-12
    )
    # Monotone in the line
    assert prob_count_over(lam, 9.5) < prob_count_over(lam, 8.5)


def test_prob_count_over_under_complement() -> None:
    ou = prob_count_over_under(10.5, 8.5)
    assert math.isclose(ou["over"] + ou["under"], 1.0, abs_tol=1e-9)


def test_total_and_half_rate() -> None:
    assert math.isclose(total_rate(5.5, 5.0), 10.5, abs_tol=1e-12)
    assert math.isclose(half_rate(10.5, 0.45), 4.725, abs_tol=1e-12)
