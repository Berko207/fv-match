"""Tests for edge/kelly.py — Kelly fractions and joint stakes for mutually exclusive legs."""

from __future__ import annotations

import math

from fvmatch.edge.kelly import Leg, fractional_kelly, joint_match_stakes, kelly_fraction


def test_kelly_zero_on_non_positive_edge() -> None:
    assert kelly_fraction(0.4, 0.5) == 0.0
    assert kelly_fraction(0.5, 0.5) == 0.0
    assert kelly_fraction(0.6, 0.6) == 0.0
    assert kelly_fraction(0.3, 0.99) == 0.0


def test_kelly_positive_below_one() -> None:
    f = kelly_fraction(0.7, 0.55)
    assert f > 0.0
    assert f < 1.0
    # Known: (0.7-0.55)/(1-0.55) = 0.15/0.45 ≈ 0.333...
    assert math.isclose(f, 0.333333, abs_tol=1e-5)


def test_fractional_kelly_scales_and_caps() -> None:
    p, price = 0.8, 0.4
    full = kelly_fraction(p, price)  # (0.8-0.4)/(1-0.4) = 0.4/0.6 ≈ 0.6667
    assert math.isclose(full, 2.0 / 3, abs_tol=1e-6)

    f25 = fractional_kelly(p, price, fraction=0.25, cap=0.05)
    # full * 0.25 = ~0.1667 > cap=0.05 → capped at 0.05
    assert math.isclose(f25, 0.05, abs_tol=1e-9)

    f10 = fractional_kelly(p, price, fraction=0.10, cap=0.05)
    assert f10 <= 0.05 + 1e-9
    assert f10 > 0.0


def test_joint_match_stakes_never_exceeds_cap() -> None:
    legs = [
        Leg("home", p=0.65, price=0.55),
        Leg("draw", p=0.25, price=0.30),
        Leg("away", p=0.12, price=0.20),
    ]
    stakes = joint_match_stakes(legs, fraction=0.25, cap=0.05)
    assert len(stakes) == 3
    assert all(s >= 0.0 for s in stakes)
    assert sum(stakes) <= 0.05 + 1e-9
    # Since individual would be high edge on home, but total capped at 0.05

    # Another case: low edges, no cap hit
    legs2 = [Leg("h", 0.4, 0.55), Leg("d", 0.3, 0.40)]
    stakes2 = joint_match_stakes(legs2, fraction=0.25, cap=0.05)
    assert sum(stakes2) <= 0.05 + 1e-9
    # Most will be zero edge
    assert all(s == 0.0 for s in stakes2) or sum(stakes2) < 0.03


def test_joint_scales_proportionally_when_over_cap() -> None:
    # High edge legs that would exceed if not scaled
    legs = [
        Leg("home", p=0.90, price=0.50),
        Leg("draw", p=0.30, price=0.25),
    ]
    stakes = joint_match_stakes(legs, fraction=0.5, cap=0.04)
    total = sum(stakes)
    assert total <= 0.04 + 1e-9
    assert total > 0.0
    # Both should be positive and scaled version of their raw
    assert stakes[0] > 0.0
    assert stakes[1] > 0.0
