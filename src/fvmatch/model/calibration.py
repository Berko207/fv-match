"""Model calibration diagnostics: log-loss, reliability curve, CLV aggregation.

Pure functions; no I/O. Outcomes are encoded as class indices matching the
probability vectors (e.g. 0=home, 1=draw, 2=away).
"""

from __future__ import annotations

import math
from typing import Any


def log_loss(
    y_true: list[int],
    p_pred: list[float] | list[list[float]],
    eps: float = 1e-15,
) -> float:
    """Multiclass (or binary) log-loss.

    Args:
        y_true: True class indices (e.g. 0/1/2 for H/D/A).
        p_pred: Either a list of probability vectors (one per sample) or, for a
            binary problem, a flat list of P(class==1).
        eps: Clipping to avoid log(0).

    Returns:
        Mean negative log-likelihood across samples.
    """
    if not y_true:
        return 0.0
    if len(y_true) != len(p_pred):
        raise ValueError("y_true and p_pred must be the same length")

    total = 0.0
    for i, y in enumerate(y_true):
        probs = p_pred[i]
        if isinstance(probs, (int, float)):
            p1 = min(max(float(probs), eps), 1.0 - eps)
            p = p1 if y == 1 else 1.0 - p1
        else:
            vec = [float(x) for x in probs]
            if not 0 <= y < len(vec):
                raise ValueError(f"class index {y} out of range for {len(vec)} probs")
            p = min(max(vec[y], eps), 1.0 - eps)
        total += -math.log(p)
    return total / len(y_true)


def reliability_diagram(
    model_ps: list[float],
    outcomes: list[int],
    n_bins: int = 10,
) -> dict[str, Any]:
    """Bin predicted probabilities against realized frequencies.

    Args:
        model_ps: Predicted probabilities for a single outcome (0..1).
        outcomes: 0/1 indicator of whether that outcome occurred.
        n_bins: Number of equal-width bins over [0, 1].

    Returns:
        Dict with per-bin mean predicted prob, observed frequency, count, and
        the overall expected calibration error (ECE).
    """
    if len(model_ps) != len(outcomes):
        raise ValueError("model_ps and outcomes must be the same length")
    bins_pred: list[float] = []
    bins_obs: list[float] = []
    bins_count: list[int] = []
    ece = 0.0
    n = len(model_ps) or 1
    for b in range(n_bins):
        lo = b / n_bins
        hi = (b + 1) / n_bins
        idx = [
            i
            for i, p in enumerate(model_ps)
            if (p >= lo and (p < hi or (b == n_bins - 1 and p <= hi)))
        ]
        if not idx:
            bins_pred.append(0.0)
            bins_obs.append(0.0)
            bins_count.append(0)
            continue
        mean_pred = sum(model_ps[i] for i in idx) / len(idx)
        obs = sum(outcomes[i] for i in idx) / len(idx)
        bins_pred.append(mean_pred)
        bins_obs.append(obs)
        bins_count.append(len(idx))
        ece += (len(idx) / n) * abs(mean_pred - obs)
    return {
        "bin_pred": bins_pred,
        "bin_obs": bins_obs,
        "bin_count": bins_count,
        "ece": ece,
    }


def clv_vs_market_edge(bets: list[dict[str, Any]]) -> dict[str, float]:
    """Aggregate closing-line-value stats across resolved bets.

    Each bet dict should carry ``entry_price`` and ``close_price`` (and
    optionally ``clv_pct``). Returns mean CLV %, the share of bets that beat the
    close, and the count.
    """
    rows = [
        b
        for b in bets
        if b.get("entry_price") is not None and b.get("close_price") is not None
    ]
    if not rows:
        return {"mean_clv_pct": 0.0, "beat_close_rate": 0.0, "n": 0.0}

    clvs: list[float] = []
    beats = 0
    for b in rows:
        entry = float(b["entry_price"])
        close = float(b["close_price"])
        if "clv_pct" in b and b["clv_pct"] is not None:
            clv = float(b["clv_pct"])
        elif entry > 0:
            clv = (close - entry) / entry
        else:
            continue
        clvs.append(clv)
        if clv > 0:
            beats += 1
    if not clvs:
        return {"mean_clv_pct": 0.0, "beat_close_rate": 0.0, "n": 0.0}
    return {
        "mean_clv_pct": sum(clvs) / len(clvs),
        "beat_close_rate": beats / len(clvs),
        "n": float(len(clvs)),
    }
