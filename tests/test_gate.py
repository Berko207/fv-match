"""Tests for the edge + liquidity gates."""

from __future__ import annotations

from fvmatch.edge.gate import filter_legs, passes_edge_gate, passes_liquidity_gate
from fvmatch.edge.kelly import Leg


def test_edge_gate() -> None:
    assert passes_edge_gate(0.60, 0.55, threshold=0.03) is True
    assert passes_edge_gate(0.56, 0.55, threshold=0.03) is False
    assert passes_edge_gate(0.50, 0.55, threshold=0.03) is False


def test_liquidity_gate() -> None:
    assert passes_liquidity_gate({"liquidity": 10000}, 5000) is True
    assert passes_liquidity_gate({"volume": 1000}, 5000) is False
    assert passes_liquidity_gate({}, 5000) is False  # fails closed
    assert passes_liquidity_gate({"liquidity": "bad"}, 5000) is False


def test_filter_legs_edge_only() -> None:
    legs = [
        Leg("home", p=0.60, price=0.55),
        Leg("draw", p=0.20, price=0.25),
        Leg("away", p=0.10, price=0.20),
    ]
    kept = filter_legs(legs, threshold=0.03)
    assert [leg.outcome for leg in kept] == ["home"]


def test_filter_legs_with_liquidity() -> None:
    legs = [Leg("home", p=0.60, price=0.55)]
    illiquid = filter_legs(
        legs, threshold=0.03, market_data={"liquidity": 100}, min_liquidity_usd=5000
    )
    assert illiquid == []
    liquid = filter_legs(
        legs, threshold=0.03, market_data={"liquidity": 50000}, min_liquidity_usd=5000
    )
    assert len(liquid) == 1
