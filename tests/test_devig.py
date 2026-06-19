"""Tests for edge/devig.py — deterministic de-vig methods."""

from __future__ import annotations

import math

import pytest

from fvmatch.edge.devig import devig, multiplicative, power, shin


@pytest.mark.parametrize("prices", [[1.8, 3.5, 4.2], [2.1, 2.1, 4.0], [1.5, 4.0]])
def test_multiplicative_sums_to_one(prices: list[float]) -> None:
    probs = multiplicative(prices)
    assert len(probs) == len(prices)
    assert math.isclose(sum(probs), 1.0, abs_tol=1e-12)
    assert all(0.0 <= p <= 1.0 for p in probs)


@pytest.mark.parametrize("prices", [[1.8, 3.5, 4.2], [2.1, 2.1, 4.0]])
def test_power_sums_to_one(prices: list[float]) -> None:
    probs = power(prices)
    assert len(probs) == len(prices)
    assert math.isclose(sum(probs), 1.0, abs_tol=1e-6)
    assert all(0.0 <= p <= 1.0 for p in probs)


@pytest.mark.parametrize("prices", [[1.8, 3.5, 4.2], [2.1, 2.1, 4.0], [1.01, 100.0]])
def test_shin_sums_to_one(prices: list[float]) -> None:
    probs = shin(prices)
    assert len(probs) == len(prices)
    assert math.isclose(sum(probs), 1.0, abs_tol=1e-6)
    assert all(0.0 <= p <= 1.0 for p in probs)


def test_devig_dispatcher_default_shin() -> None:
    prices = [2.0, 3.0, 6.0]
    assert devig(prices) == shin(prices)
    assert devig(prices, method="multiplicative") == multiplicative(prices)
    assert devig(prices, method="power") == power(prices)


def test_shin_power_widen_favorite_longshot_gap() -> None:
    """shin and power should widen the prob gap fav vs longshot vs multiplicative."""
    prices = [1.8, 3.8, 5.5]  # overround ~0.05%
    p_multi = multiplicative(prices)
    p_shin = shin(prices)
    p_power = power(prices)

    # Favorite (first) gets relatively more (or equal within fp) in shin/power
    assert p_shin[0] >= p_multi[0] - 1e-9
    assert p_power[0] >= p_multi[0] - 1e-9

    # Gap between max and min widens or stays (for tiny overround)
    def gap(ps: list[float]) -> float:
        return max(ps) - min(ps)

    assert gap(p_shin) >= gap(p_multi) - 1e-9
    assert gap(p_power) >= gap(p_multi) - 1e-9


def test_edge_cases_empty_and_single() -> None:
    assert multiplicative([]) == []
    assert shin([]) == []
    assert power([]) == []
    assert devig([2.5]) == [1.0]  # single outcome edge case
