"""STUB: Ingest final scores / results resolution."""

from __future__ import annotations

from fvmatch.data.store import Store


def backfill_results(
    store: Store,
    competition: str,
    season: str,
    api_key: str | None = None,
) -> int:
    """Backfill final scores (home_goals, away_goals) for resolved fixtures.

    Used for model training and bet resolution.
    Phase 0: STUB.
    """
    raise NotImplementedError("results.backfill_results is a Phase 0 stub")


def resolve_pending_bets(store: Store) -> int:
    """Find resolved fixtures with pending bets and update realized_pnl via accounting."""
    raise NotImplementedError("results.resolve_pending_bets is a Phase 0 stub")
