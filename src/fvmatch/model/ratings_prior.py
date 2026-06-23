"""Elo ratings used as the strength prior for the goal-expectation model.

For international football many teams play sparsely, so a stable Elo prior is a
better anchor than a from-scratch attack/defence fit. These functions are pure
and deterministic; the bundled ratings (``data/seed/international_elo.json``) are
illustrative defaults and should be recalibrated from real results before any
live use.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_SEED_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "seed" / "international_elo.json"
)

DEFAULT_ELO = 1600.0


@lru_cache(maxsize=1)
def load_seed_ratings() -> dict[str, float]:
    """Load the bundled national-team Elo ratings (team name -> rating)."""
    if not _SEED_PATH.exists():
        return {}
    raw = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
    ratings = raw.get("ratings", {})
    return {str(k): float(v) for k, v in ratings.items()}


def _normalize(name: str) -> str:
    return name.strip().casefold()


def get_rating(
    team: str,
    ratings: dict[str, float] | None = None,
    default: float = DEFAULT_ELO,
) -> float:
    """Return the Elo rating for ``team`` (case-insensitive), or ``default``.

    Args:
        team: Team name.
        ratings: Optional ratings map; falls back to the bundled seed.
        default: Rating to use when the team is unknown.
    """
    table = ratings if ratings is not None else load_seed_ratings()
    if team in table:
        return table[team]
    lookup = {_normalize(k): v for k, v in table.items()}
    return lookup.get(_normalize(team), default)


def expected_score(elo_a: float, elo_b: float) -> float:
    """Logistic Elo expectation that A beats B (draw counted as half).

    Returns a value in (0, 1); 0.5 means evenly matched.
    """
    return 1.0 / (1.0 + float(10.0 ** (-(elo_a - elo_b) / 400.0)))


def elo_update(
    elo_a: float,
    elo_b: float,
    score_a: float,
    k: float = 30.0,
    goal_diff: int = 0,
) -> tuple[float, float]:
    """Return updated (elo_a, elo_b) after a match.

    Args:
        elo_a, elo_b: Pre-match ratings.
        score_a: Actual result for A (1 win, 0.5 draw, 0 loss).
        k: K-factor (base learning rate).
        goal_diff: Absolute goal margin; widens the update for blowouts
            using the World Football Elo multiplier.
    """
    margin = abs(goal_diff)
    multiplier = 1.0
    if margin == 2:
        multiplier = 1.5
    elif margin > 2:
        multiplier = (11.0 + margin) / 8.0
    exp_a = expected_score(elo_a, elo_b)
    delta = k * multiplier * (score_a - exp_a)
    return elo_a + delta, elo_b - delta


def elo_prior(
    team_id: int | str,
    competition_kind: str = "international",
    base_elo: float = DEFAULT_ELO,
) -> float:
    """Return an Elo rating prior for a team (bundled seed lookup by name)."""
    return get_rating(str(team_id), default=base_elo)


def blend_team_ratings(
    team_ids: list[int | str],
    store_ratings: dict[int | str, float],
    competition: str = "international",
) -> dict[int | str, float]:
    """Blend stored ratings with the bundled prior for the given teams.

    Stored ratings take precedence; missing teams fall back to the seed prior.
    """
    blended: dict[int | str, float] = {}
    for tid in team_ids:
        if tid in store_ratings:
            blended[tid] = store_ratings[tid]
        else:
            blended[tid] = get_rating(str(tid))
    return blended
