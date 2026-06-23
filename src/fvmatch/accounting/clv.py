"""Closing-line value (CLV) — the project's north-star validation metric.

CLV measures whether we consistently transacted at a better price than the
market's closing line. Beating the close is evidence of genuine edge that does
not depend on the (high-variance) match result.
"""

from __future__ import annotations

from typing import Any


def compute_clv(
    entry_price: float,
    close_price: float,
    model_p: float | None = None,
) -> float:
    """Closing-line value as a fractional price improvement.

    For a backable share that pays $1, a *lower* entry price than the close is
    favourable, so::

        clv = (close_price - entry_price) / entry_price

    Positive means we bought cheaper than the close (beat the market).
    ``model_p`` is accepted for interface symmetry and ignored here.
    """
    if entry_price <= 0:
        raise ValueError("entry_price must be > 0")
    return (close_price - entry_price) / entry_price


def clv_for_bet(bet_id: int | str, store: Any) -> dict[str, float]:
    """Fetch entry vs close for a bet and compute CLV.

    ``store`` may be a mapping ``bet_id -> {entry_price, close_price, model_p}``
    or any object exposing a ``get_bet(bet_id)`` method returning that dict.
    """
    record: dict[str, Any] | None
    if hasattr(store, "get_bet"):
        record = store.get_bet(bet_id)
    elif isinstance(store, dict):
        record = store.get(bet_id)
    else:
        record = None
    if not record:
        raise KeyError(f"No bet record for id {bet_id!r}")

    entry = float(record["entry_price"])
    close = float(record["close_price"])
    model_p = record.get("model_p")
    clv = compute_clv(entry, close, model_p)
    return {
        "entry_price": entry,
        "close_price": close,
        "clv": clv,
        "clv_pct": clv * 100.0,
    }
