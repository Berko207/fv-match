"""Tests for calibration diagnostics."""

from __future__ import annotations

import math

from fvmatch.model.calibration import (
    clv_vs_market_edge,
    log_loss,
    reliability_diagram,
)


def test_log_loss_binary() -> None:
    # Perfect-ish predictions → low loss
    loss = log_loss([1, 0], [0.99, 0.01])
    assert loss < 0.05
    # Confidently wrong → high loss
    bad = log_loss([1, 0], [0.01, 0.99])
    assert bad > 3.0


def test_log_loss_multiclass() -> None:
    loss = log_loss([0, 2], [[0.8, 0.1, 0.1], [0.1, 0.2, 0.7]])
    expected = -(math.log(0.8) + math.log(0.7)) / 2
    assert math.isclose(loss, expected, abs_tol=1e-9)


def test_reliability_diagram_perfect() -> None:
    ps = [0.05, 0.15, 0.95, 0.85]
    obs = [0, 0, 1, 1]
    out = reliability_diagram(ps, obs, n_bins=10)
    assert out["ece"] < 0.2
    assert sum(out["bin_count"]) == 4


def test_clv_vs_market_edge() -> None:
    bets = [
        {"entry_price": 0.5, "close_price": 0.55},
        {"entry_price": 0.5, "close_price": 0.45},
        {"entry_price": 0.4, "close_price": 0.44},
    ]
    stats = clv_vs_market_edge(bets)
    assert stats["n"] == 3.0
    assert math.isclose(stats["beat_close_rate"], 2 / 3, abs_tol=1e-9)


def test_clv_vs_market_edge_empty() -> None:
    assert clv_vs_market_edge([])["n"] == 0.0
