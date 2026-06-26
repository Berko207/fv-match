"""Derived goals-market pricers: one Dixon-Coles scoreline matrix → many markets.

The engine already computes a single ``P(home=i, away=j)`` scoreline grid for a
fixture (see :mod:`fvmatch.model.dixon_coles`). Almost every *goals-derived*
Polymarket market on a match — totals, both-teams-to-score, exact score, team
totals, double chance, draw-no-bet, winning margin, odd/even — is just a sum
over cells of that one grid. Pricing them is therefore free: no extra fit, no
network, fully deterministic.

Half markets (1st-half total / result) need a half scoreline grid. We build one
by scaling each side's goal expectation by ``first_half_goal_share`` (~0.45 of a
match's goals fall in the first half) and re-running the same machinery. This is
an approximation — documented as such — not a separately fitted half model.

Everything here is pure and operates on a normalized scoreline matrix; nothing
reads config or the network.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from fvmatch.model.dixon_coles import scoreline_matrix

Matrix = NDArray[np.float64]


# --- distributions derived from the scoreline grid ---------------------------


def total_goals_pmf(matrix: Matrix) -> NDArray[np.float64]:
    """Probability of each total-goals value ``k = 0 .. 2*max_goals``."""
    rows, cols = matrix.shape
    pmf = np.zeros(rows + cols - 1, dtype=np.float64)
    for i in range(rows):
        for j in range(cols):
            pmf[i + j] += matrix[i, j]
    return pmf


def goal_difference_pmf(matrix: Matrix) -> tuple[NDArray[np.float64], int]:
    """Distribution of ``home - away`` goals.

    Returns ``(pmf, offset)`` where ``pmf[d + offset] = P(home - away == d)`` so
    a fully negative margin (heavy away win) is representable. ``offset`` equals
    ``cols - 1`` (the most negative achievable difference).
    """
    rows, cols = matrix.shape
    offset = cols - 1
    pmf = np.zeros(rows + cols - 1, dtype=np.float64)
    for i in range(rows):
        for j in range(cols):
            pmf[(i - j) + offset] += matrix[i, j]
    return pmf, offset


# --- 1X2-family markets ------------------------------------------------------


def prob_hda(matrix: Matrix) -> tuple[float, float, float]:
    """``(home, draw, away)`` win probabilities (re-export for convenience)."""
    p_home = float(np.tril(matrix, k=-1).sum())
    p_draw = float(np.trace(matrix))
    p_away = float(np.triu(matrix, k=1).sum())
    return p_home, p_draw, p_away


def prob_double_chance(matrix: Matrix) -> dict[str, float]:
    """``1X`` (home or draw), ``12`` (home or away), ``X2`` (draw or away)."""
    h, d, a = prob_hda(matrix)
    return {"1X": h + d, "12": h + a, "X2": d + a}


def prob_draw_no_bet(matrix: Matrix) -> dict[str, float]:
    """Draw-no-bet: win probabilities conditioned on a non-draw (stake refunded)."""
    h, d, a = prob_hda(matrix)
    live = h + a
    if live <= 0:
        return {"home": 0.0, "away": 0.0}
    return {"home": h / live, "away": a / live}


# --- totals / BTTS / team totals --------------------------------------------


def prob_total_over(matrix: Matrix, line: float) -> float:
    """``P(total goals > line)``. ``line`` is a half-line such as 2.5."""
    pmf = total_goals_pmf(matrix)
    ks = np.arange(len(pmf))
    return float(pmf[ks > line].sum())


def prob_total_over_under(matrix: Matrix, line: float) -> dict[str, float]:
    """``{"over", "under"}`` for a goals total line."""
    over = prob_total_over(matrix, line)
    return {"over": over, "under": 1.0 - over}


def prob_both_teams_to_score(matrix: Matrix) -> dict[str, float]:
    """``{"yes", "no"}`` for both teams scoring at least one goal."""
    p_home_zero = float(matrix[0, :].sum())
    p_away_zero = float(matrix[:, 0].sum())
    p_both_zero = float(matrix[0, 0])
    p_no = p_home_zero + p_away_zero - p_both_zero  # at least one side blank
    return {"yes": 1.0 - p_no, "no": p_no}


def prob_team_total_over(matrix: Matrix, line: float, side: str) -> float:
    """``P(side's goals > line)`` for ``side in {"home", "away"}``."""
    if side == "home":
        marginal = matrix.sum(axis=1)
    elif side == "away":
        marginal = matrix.sum(axis=0)
    else:  # pragma: no cover - guarded by callers
        raise ValueError(f"side must be 'home' or 'away', got {side!r}")
    ks = np.arange(len(marginal))
    return float(marginal[ks > line].sum())


def prob_team_total_over_under(
    matrix: Matrix, line: float, side: str
) -> dict[str, float]:
    over = prob_team_total_over(matrix, line, side)
    return {"over": over, "under": 1.0 - over}


def prob_clean_sheet(matrix: Matrix, side: str) -> dict[str, float]:
    """``{"yes", "no"}`` that ``side`` concedes zero goals."""
    if side == "home":
        yes = float(matrix[:, 0].sum())  # away scores 0
    elif side == "away":
        yes = float(matrix[0, :].sum())  # home scores 0
    else:  # pragma: no cover
        raise ValueError(f"side must be 'home' or 'away', got {side!r}")
    return {"yes": yes, "no": 1.0 - yes}


# --- exact score / margin / parity ------------------------------------------


def prob_exact_score(matrix: Matrix, home: int, away: int) -> float:
    """``P(home scores `home`, away scores `away`)`` (tail outcomes clamp to 0)."""
    rows, cols = matrix.shape
    if 0 <= home < rows and 0 <= away < cols:
        return float(matrix[home, away])
    return 0.0


def prob_winning_margin(matrix: Matrix, margin: int, side: str) -> float:
    """``P(side wins by exactly `margin` goals)`` (``margin`` >= 1)."""
    pmf, offset = goal_difference_pmf(matrix)
    d = margin if side == "home" else -margin
    idx = d + offset
    if 0 <= idx < len(pmf):
        return float(pmf[idx])
    return 0.0


def prob_odd_even_total(matrix: Matrix) -> dict[str, float]:
    """``{"odd", "even"}`` total goals (0 counts as even)."""
    pmf = total_goals_pmf(matrix)
    ks = np.arange(len(pmf))
    even = float(pmf[ks % 2 == 0].sum())
    return {"even": even, "odd": 1.0 - even}


# --- halves ------------------------------------------------------------------


def first_half_matrix(
    lam_home: float,
    lam_away: float,
    *,
    first_half_goal_share: float = 0.45,
    rho: float = -0.08,
    max_goals: int = 10,
) -> Matrix:
    """Approximate first-half scoreline grid by scaling each side's lambda.

    ~45% of a match's goals fall in the first half; we scale both expectations
    by ``first_half_goal_share`` and re-run the Dixon-Coles grid. This is an
    approximation (no separately fitted half model), adequate for half totals
    and half result markets.
    """
    return scoreline_matrix(
        lam_home * first_half_goal_share,
        lam_away * first_half_goal_share,
        rho=rho,
        max_goals=max_goals,
    )
