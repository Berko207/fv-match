"""STUB: Thin adapter to existing Polymarket CLOB v2 execution bot.

This module never places orders itself when DRY_RUN=true (the default).
It becomes a no-op or logger in dry-run; real orders only via the external bot
when explicitly enabled and after all gates (incl. positive CLV historically).
"""

from __future__ import annotations

from typing import Any

from fvmatch.config import settings
from fvmatch.edge.kelly import Leg


def place_bets(
    legs: list[Leg],
    stakes: list[float],
    fixture_id: int | str,
    dry_run: bool | None = None,
) -> list[dict[str, Any]]:
    """Submit stakes to CLOB bot for the given legs on one match.

    If dry_run (default from settings), log only and return simulated fills.
    Real execution path requires DRY_RUN=false AND CLV validation passed.
    Phase 0: STUB — always behaves as dry_run.
    """
    effective_dry = dry_run if dry_run is not None else settings.dry_run
    if effective_dry:
        return [
            {
                "leg": leg.outcome,
                "stake": stake,
                "status": "simulated",
                "tx_hash": None,
            }
            for leg, stake in zip(legs, stakes, strict=True)
        ]
    raise NotImplementedError(
        "Real CLOB execution not wired in Phase 0. "
        "See execution.client and existing bot integration."
    )


def cancel_all_pending(fixture_id: int | str | None = None) -> int:
    """Cancel any open orders for a fixture (risk management)."""
    raise NotImplementedError("execution.cancel_all_pending is a Phase 0 stub")
