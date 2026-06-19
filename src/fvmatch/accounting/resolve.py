"""STUB: Outcome resolution → realized P&L update."""

from __future__ import annotations

from typing import Any


def resolve_bet(
    bet_row: dict[str, Any],
    fixture_result: dict[str, Any],
) -> float:
    """Given bet and final score, compute realized_pnl (positive if win).

    Uses entry_price and stake to calc payout.
    Phase 0: STUB.
    """
    raise NotImplementedError("resolve.resolve_bet is a Phase 0 stub")


def batch_resolve(store_bets: list[dict[str, Any]]) -> int:
    """Resolve all pending bets for recently finished fixtures."""
    raise NotImplementedError("resolve.batch_resolve is a Phase 0 stub")
