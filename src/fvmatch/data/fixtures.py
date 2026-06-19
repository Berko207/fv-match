"""STUB: Ingest fixtures (league history + Gamma live)."""

from __future__ import annotations

from typing import Any

from fvmatch.data.store import Store


def backfill_fixtures(
    store: Store,
    competition: str,
    season: str,
    api_key: str | None = None,
    limit: int = 1000,
) -> int:
    """Backfill historical fixtures + kickoff times for a competition/season.

    Sources: football-data.org (or configured provider) + external_ids.
    Phase 0: STUB — returns count of upserted rows.
    """
    raise NotImplementedError("fixtures.backfill_fixtures is a Phase 0 stub")


def poll_upcoming(
    store: Store, hours_ahead: int = 48, source: str = "gamma"
) -> list[dict[str, Any]]:
    """Poll live/upcoming fixtures from Gamma (or other) for model + edge."""
    raise NotImplementedError("fixtures.poll_upcoming is a Phase 0 stub")
