"""STUB: Edge threshold + liquidity gate before proposing bet."""

from __future__ import annotations

from typing import Any

from fvmatch.edge.kelly import Leg


def passes_edge_gate(
    model_p: float,
    market_price: float,
    threshold: float = 0.03,
) -> bool:
    """True if (model_p - de_vigged_price) > threshold after de-vig."""
    raise NotImplementedError("gate.passes_edge_gate is a Phase 0 stub")


def passes_liquidity_gate(
    market_snapshot: dict[str, Any],
    min_liquidity_usd: float = 5000.0,
) -> bool:
    """Check CLOB depth / Gamma volume sufficient for stake size."""
    raise NotImplementedError("gate.passes_liquidity_gate is a Phase 0 stub")


def filter_legs(
    legs: list[Leg],
    threshold: float,
    market_data: dict[str, Any],
) -> list[Leg]:
    """Return only legs that pass both edge and liquidity gates."""
    raise NotImplementedError("gate.filter_legs is a Phase 0 stub")
