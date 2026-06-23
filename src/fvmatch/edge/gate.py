"""Edge + liquidity gates: decide which legs are worth betting.

A leg clears the gate only when the model's probability exceeds the (de-vigged)
market price by more than ``threshold`` AND the market is liquid enough to
absorb a stake. Prices/probabilities are expressed as cost-per-$1-share in
[0, 1] (Polymarket convention), so ``edge = model_p - market_price``.
"""

from __future__ import annotations

from typing import Any

from fvmatch.edge.kelly import Leg


def passes_edge_gate(
    model_p: float,
    market_price: float,
    threshold: float = 0.03,
) -> bool:
    """True if model probability beats the de-vigged price by > ``threshold``."""
    return (model_p - market_price) > threshold


def passes_liquidity_gate(
    market_snapshot: dict[str, Any],
    min_liquidity_usd: float = 5000.0,
) -> bool:
    """True if the market has enough liquidity/volume to support a stake.

    Looks for ``liquidity``, ``liquidity_usd`` or ``volume`` on the snapshot.
    Missing liquidity data fails closed (returns ``False``).
    """
    for key in ("liquidity_usd", "liquidity", "volume"):
        value = market_snapshot.get(key)
        if value is not None:
            try:
                return float(value) >= min_liquidity_usd
            except (TypeError, ValueError):
                return False
    return False


def filter_legs(
    legs: list[Leg],
    threshold: float,
    market_data: dict[str, Any] | None = None,
    min_liquidity_usd: float = 5000.0,
) -> list[Leg]:
    """Return only legs clearing both the edge and liquidity gates.

    Args:
        legs: Candidate legs (``p`` = model prob, ``price`` = de-vigged price).
        threshold: Minimum edge.
        market_data: Optional per-outcome liquidity info, either a flat snapshot
            applied to every leg, or ``{outcome: snapshot}``. When omitted the
            liquidity gate is skipped (edge gate only).
        min_liquidity_usd: Liquidity threshold passed to the liquidity gate.
    """
    kept: list[Leg] = []
    for leg in legs:
        if not passes_edge_gate(leg.p, leg.price, threshold):
            continue
        if market_data:
            snapshot = market_data.get(leg.outcome, market_data)
            if isinstance(snapshot, dict) and not passes_liquidity_gate(
                snapshot, min_liquidity_usd
            ):
                continue
        kept.append(leg)
    return kept
