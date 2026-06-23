"""In-play conditional scoreline model: remaining goals from pre-match lambdas.

Pre-match ``lam_home`` / ``lam_away`` are full-match expectations from
:func:`~fvmatch.model.dixon_coles.lambdas_from_elo`. Given elapsed time, the
current score, and optional red cards, we derive a final-score probability grid
by convolving independent remaining Poisson goals (Dixon-Coles ``rho`` applies
only at kickoff).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from fvmatch.model.dixon_coles import marginal_hda, scoreline_matrix

# Placeholder — tune vs historical in-play goal-rate curves (e.g. EPL minute bins).
# Linear rise from 1.0 at kickoff to ``1 + RISING_LATE_GAME_SLOPE`` at full time.
RISING_LATE_GAME_SLOPE: float = 0.30

# Placeholder — tune vs red-card event studies; one man down ~25% fewer goals scored.
RED_CARD_SELF: float = 0.75
# Placeholder — opponent modestly benefits from numerical advantage.
RED_CARD_OPP: float = 1.10


@dataclass(frozen=True)
class LiveState:
    """Snapshot of an in-progress fixture."""

    minute: float
    home_goals: int
    away_goals: int
    red_cards_home: int = 0
    red_cards_away: int = 0
    match_length: float = 90.0


def _clamp_minute(minute: float, match_length: float) -> float:
    return float(np.clip(minute, 0.0, match_length))


def _remaining_fraction(
    minute: float,
    match_length: float,
    intensity_profile: str,
) -> float:
    """Fraction of full-match expected goals still to be scored."""
    if match_length <= 0:
        return 0.0
    u0 = _clamp_minute(minute, match_length) / match_length
    remaining_time = 1.0 - u0
    if remaining_time <= 0.0:
        return 0.0
    if intensity_profile == "uniform":
        return remaining_time
    if intensity_profile == "rising":
        slope = RISING_LATE_GAME_SLOPE
        # ∫₀¹ (1 + slope·u) du — total goal-intensity weight over the match.
        full_weight = 1.0 + slope / 2.0
        # ∫_{u0}¹ (1 + slope·u) du — weight left in remaining minutes.
        remaining_weight = remaining_time + slope * (1.0 - u0**2) / 2.0
        return remaining_weight / full_weight
    raise ValueError(
        f"intensity_profile must be 'uniform' or 'rising', got {intensity_profile!r}"
    )


def _red_card_factors(state: LiveState) -> tuple[float, float]:
    """Multiplicative scoring adjustments for remaining-time lambdas."""
    home_factor = (RED_CARD_SELF**state.red_cards_home) * (
        RED_CARD_OPP**state.red_cards_away
    )
    away_factor = (RED_CARD_SELF**state.red_cards_away) * (
        RED_CARD_OPP**state.red_cards_home
    )
    return home_factor, away_factor


def _point_mass_matrix(
    home_goals: int,
    away_goals: int,
    max_goals: int,
) -> NDArray[np.float64]:
    """Degenerate final-score matrix when no time remains."""
    matrix = np.zeros((max_goals + 1, max_goals + 1), dtype=np.float64)
    i = min(home_goals, max_goals)
    j = min(away_goals, max_goals)
    matrix[i, j] = 1.0
    return matrix


def _shift_remaining_matrix(
    remaining: NDArray[np.float64],
    home_goals: int,
    away_goals: int,
    max_goals: int,
) -> NDArray[np.float64]:
    """Add current score to remaining goals; fold overflow into last row/col."""
    size = max_goals + 1
    final = np.zeros((size, size), dtype=np.float64)
    rem_rows, rem_cols = remaining.shape
    for i in range(rem_rows):
        for j in range(rem_cols):
            mass = remaining[i, j]
            if mass <= 0.0:
                continue
            fi = home_goals + i
            fj = away_goals + j
            if fi >= size:
                fi = size - 1
            if fj >= size:
                fj = size - 1
            final[fi, fj] += mass
    total = final.sum()
    if total <= 0.0:
        raise ValueError("Degenerate conditional scoreline matrix (non-positive mass)")
    return final / total


def conditional_scoreline_matrix(
    lam_home: float,
    lam_away: float,
    state: LiveState,
    rho: float = -0.08,
    max_goals: int = 10,
    intensity_profile: str = "uniform",
) -> NDArray[np.float64]:
    """Return ``P(final_home=i, final_away=j)`` conditioned on ``state``.

    See module docstring and inline comments for the five-step method.
    """
    minute = _clamp_minute(state.minute, state.match_length)
    f = _remaining_fraction(minute, state.match_length, intensity_profile)

    if f <= 0.0:
        return _point_mass_matrix(state.home_goals, state.away_goals, max_goals)

    red_home, red_away = _red_card_factors(state)
    remaining_lam_home = lam_home * f * red_home
    remaining_lam_away = lam_away * f * red_away

    # Dixon-Coles tau is a kickoff low-score effect; remaining goals are ~Poisson.
    remaining_rho = rho if minute == 0.0 else 0.0
    remaining = scoreline_matrix(
        remaining_lam_home,
        remaining_lam_away,
        rho=remaining_rho,
        max_goals=max_goals,
    )
    return _shift_remaining_matrix(
        remaining, state.home_goals, state.away_goals, max_goals
    )


def live_hda(
    lam_home: float,
    lam_away: float,
    state: LiveState,
    *,
    rho: float = -0.08,
    max_goals: int = 10,
    intensity_profile: str = "uniform",
) -> tuple[float, float, float]:
    """Marginal home/draw/away from the conditional final-score matrix."""
    matrix = conditional_scoreline_matrix(
        lam_home,
        lam_away,
        state,
        rho=rho,
        max_goals=max_goals,
        intensity_profile=intensity_profile,
    )
    return marginal_hda(matrix)
