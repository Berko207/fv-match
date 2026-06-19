"""STUB: Closing-line value (CLV) computation — the project's true north metric."""

from __future__ import annotations

from typing import Any


def compute_clv(
    entry_price: float,
    close_price: float,
    model_p: float,
) -> float:
    """CLV % = (model_p - close_price) / close_price or signed edge at close.

    Positive CLV means we got better price than close (or model still liked it).
    Primary validation that edge was real ex-ante.
    """
    raise NotImplementedError("clv.compute_clv is a Phase 0 stub")


def clv_for_bet(bet_id: int | str, store: Any) -> dict[str, float]:
    """Fetch entry vs close for a bet and compute CLV + pct improvement."""
    raise NotImplementedError("clv.clv_for_bet is a Phase 0 stub")
