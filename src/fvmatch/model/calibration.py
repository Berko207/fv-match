"""STUB: Model calibration diagnostics (log-loss, reliability vs market)."""

from __future__ import annotations

from typing import Any


def log_loss(
    y_true: list[int],
    p_pred: list[float],
    eps: float = 1e-15,
) -> float:
    """Standard multiclass log-loss for H/D/A calibration."""
    raise NotImplementedError("calibration.log_loss is a Phase 0 stub")


def reliability_diagram(
    model_ps: list[float],
    outcomes: list[int],
    n_bins: int = 10,
) -> dict[str, Any]:
    """Compute reliability (calibration) curve vs binned model probs."""
    raise NotImplementedError("calibration.reliability_diagram is a Phase 0 stub")


def clv_vs_market_edge(
    bets: list[dict[str, Any]],
) -> dict[str, float]:
    """Aggregate CLV stats and edge vs closing line for validation."""
    raise NotImplementedError("calibration.clv_vs_market_edge is a Phase 0 stub")
