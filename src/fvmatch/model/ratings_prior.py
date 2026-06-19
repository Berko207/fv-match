"""STUB: Elo (or other) prior for anchoring sparse teams in international comps."""

from __future__ import annotations


def elo_prior(
    team_id: int | str,
    competition_kind: str,
    base_elo: float = 1500.0,
) -> float:
    """Return Elo rating prior. For sparse teams blends league Elo + FIFA/UEFA rank prior."""
    raise NotImplementedError("ratings_prior.elo_prior is a Phase 0 stub")


def blend_team_ratings(
    team_ids: list[int | str],
    store_ratings: dict[int | str, float],
    competition: str,
) -> dict[int | str, float]:
    """Blend stored ratings with prior for international fixtures."""
    raise NotImplementedError("ratings_prior.blend_team_ratings is a Phase 0 stub")
