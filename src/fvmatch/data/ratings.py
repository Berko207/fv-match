"""STUB: Elo prior ingest / compute for sparse teams (esp. international)."""

from __future__ import annotations

from typing import Any

from fvmatch.data.store import Store


def compute_elo_ratings(
    store: Store,
    as_of: str | None = None,
    source: str = "internal",
) -> int:
    """Compute or update team_ratings (Elo or Massey) as_of date.

    Anchors sparse teams (e.g. WC qualifiers) to league Elo or FIFA ranking prior.
    Phase 0: STUB.
    """
    raise NotImplementedError("ratings.compute_elo_ratings is a Phase 0 stub")


def get_ratings_prior(
    store: Store, team_ids: list[int | str]
) -> dict[int | str, float]:
    """Return latest rating dict for given teams (for model prior)."""
    raise NotImplementedError("ratings.get_ratings_prior is a Phase 0 stub")
