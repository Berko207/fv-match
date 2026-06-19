"""Tests for CLOB V2 execution adapter (dry-run + pure helpers)."""

from __future__ import annotations

import pytest

from fvmatch.config import Settings
from fvmatch.edge.kelly import Leg
from fvmatch.execution.client import cancel_all_pending, place_bets
from fvmatch.execution.clob import (
    apply_buy_slippage,
    stake_fraction_to_shares,
)


def test_stake_fraction_to_shares() -> None:
    shares, cost = stake_fraction_to_shares(0.02, 1000.0, 0.5)
    assert cost == pytest.approx(20.0)
    assert shares == pytest.approx(40.0)


def test_stake_fraction_zero_on_bad_inputs() -> None:
    assert stake_fraction_to_shares(0.0, 1000.0, 0.5) == (0.0, 0.0)
    assert stake_fraction_to_shares(0.02, 0.0, 0.5) == (0.0, 0.0)
    assert stake_fraction_to_shares(0.02, 1000.0, 0.0) == (0.0, 0.0)


def test_apply_buy_slippage_caps_below_one() -> None:
    assert apply_buy_slippage(0.50, 50) == pytest.approx(0.5025)
    assert apply_buy_slippage(0.999, 500) == pytest.approx(0.9999)


def test_place_bets_dry_run_default() -> None:
    legs = [Leg(outcome="home", p=0.5, price=0.45)]
    fills = place_bets(legs, [0.02], fixture_id=1, dry_run=True)
    assert len(fills) == 1
    assert fills[0]["status"] == "simulated"
    assert fills[0]["order_id"] is None


def test_place_bets_live_requires_gates(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = Settings(
        dry_run=False,
        clv_validation_passed=False,
        polymarket_private_key="abc123",
        polymarket_bankroll_pusd=100.0,
    )
    monkeypatch.setattr("fvmatch.execution.client.settings", cfg)
    legs = [Leg(outcome="home", p=0.5, price=0.45)]
    with pytest.raises(RuntimeError, match="CLV_VALIDATION_PASSED"):
        place_bets(
            legs,
            [0.02],
            fixture_id=1,
            token_ids={"home": "token-1"},
            dry_run=False,
        )


def test_cancel_all_pending_dry_run() -> None:
    assert cancel_all_pending(fixture_id=99) == 0
