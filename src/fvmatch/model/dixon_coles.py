"""STUB: Dixon-Coles model fit + predict (scoreline matrix + H/D/A).

Dixon-Coles extends bivariate Poisson with time-decay and low-score correlation (rho).
"""

from __future__ import annotations

from typing import Any

import numpy as np


def fit(
    fixtures: list[dict[str, Any]],
    ratings: dict[int | str, float] | None = None,
    decay_lambda: float = 0.003,
    rho: float = 0.0,
) -> dict[str, Any]:
    """Fit Dixon-Coles parameters on historical fixtures.

    Returns dict with attack/defence params per team, rho, etc.
    Phase 0: STUB — will use scipy.optimize or closed form approx.
    """
    raise NotImplementedError("dixon_coles.fit is a Phase 0 stub")


def predict_scoreline_matrix(
    home_team_id: int | str,
    away_team_id: int | str,
    params: dict[str, Any],
    max_goals: int = 6,
) -> np.ndarray:
    """Return (max_goals+1, max_goals+1) matrix of P(home_goals=i, away_goals=j)."""
    raise NotImplementedError("dixon_coles.predict_scoreline_matrix is a Phase 0 stub")


def marginal_hda(p_matrix: np.ndarray) -> tuple[float, float, float]:
    """Sum matrix to get (p_home, p_draw, p_away)."""
    raise NotImplementedError("dixon_coles.marginal_hda is a Phase 0 stub")
