"""Tests for accounting: P&L resolution and CLV."""

from __future__ import annotations

import math

import pytest

from fvmatch.accounting.clv import clv_for_bet, compute_clv
from fvmatch.accounting.resolve import batch_resolve, resolve_bet


def test_resolve_bet_win_and_loss() -> None:
    bet = {"outcome": "home", "stake": 100.0, "entry_price": 0.5}
    win = resolve_bet(bet, {"home_goals": 2, "away_goals": 0})
    # 100 buys 200 shares @0.5; payout 200; profit 100
    assert math.isclose(win, 100.0, abs_tol=1e-9)
    loss = resolve_bet(bet, {"home_goals": 0, "away_goals": 1})
    assert math.isclose(loss, -100.0, abs_tol=1e-9)


def test_resolve_bet_draw() -> None:
    bet = {"outcome": "draw", "stake": 50.0, "entry_price": 0.25}
    pnl = resolve_bet(bet, {"home_goals": 1, "away_goals": 1})
    assert math.isclose(pnl, 150.0, abs_tol=1e-9)  # 200 shares - 50 stake


def test_resolve_bet_invalid_price() -> None:
    with pytest.raises(ValueError):
        resolve_bet(
            {"outcome": "home", "stake": 10.0, "entry_price": 0.0},
            {"home_goals": 1, "away_goals": 0},
        )


def test_batch_resolve_counts() -> None:
    bets = [
        {
            "outcome": "home",
            "stake": 10.0,
            "entry_price": 0.5,
            "fixture_result": {"home_goals": 1, "away_goals": 0},
        },
        {"outcome": "away", "stake": 10.0, "entry_price": 0.5},  # no result
    ]
    n = batch_resolve(bets)
    assert n == 1
    assert bets[0]["status"] == "resolved"
    assert bets[0]["realized_pnl"] == 10.0


def test_compute_clv() -> None:
    # Bought at 0.50, close at 0.55 → beat the close
    assert math.isclose(compute_clv(0.50, 0.55), 0.10, abs_tol=1e-9)
    assert compute_clv(0.55, 0.50) < 0


def test_clv_for_bet_dict_store() -> None:
    store = {7: {"entry_price": 0.4, "close_price": 0.44, "model_p": 0.5}}
    out = clv_for_bet(7, store)
    assert math.isclose(out["clv"], 0.10, abs_tol=1e-9)
    assert math.isclose(out["clv_pct"], 10.0, abs_tol=1e-9)
