"""Prior-based Poisson models for peripheral count markets: corners, shots, assists.

The goals model is the engine's calibrated core. Corners / shots / assists are a
*different* stochastic process the scoreline grid says nothing about, yet
Polymarket lists totals and team-totals on them. This module prices those with
the same philosophy the goals model uses for sparse international fixtures: an
**Elo-supremacy prior**, not a from-scratch fit.

Each market gets a base match total (e.g. ~10.5 corners) split between the two
sides by Elo supremacy — the stronger side earns more corners/shots — yielding
two independent Poisson rates. Totals are then a Poisson on the summed rate;
team-totals use the per-side rate; half lines scale by a half-share.

IMPORTANT: these rates are **uncalibrated priors**, not fitted from corner/shot
data (the repo ships only Elo ratings). They make the markets *priceable and
comparable* to the market line, but the numbers must be calibrated against real
corner/shot data — and clear the positive-CLV gate — before any live money.
Treat their edges as hypotheses, not signals, until then.
"""

from __future__ import annotations

import math

_RATE_FLOOR = 0.05


def count_lambdas(
    elo_home: float,
    elo_away: float,
    base_total: float,
    *,
    scale: float,
    home_advantage: float = 0.0,
) -> tuple[float, float]:
    """Split a base match total into ``(lambda_home, lambda_away)`` by Elo supremacy.

    Mirrors :func:`fvmatch.model.dixon_coles.lambdas_from_elo` but for an
    arbitrary count market. ``scale`` is Elo points per one unit of count
    supremacy (larger ``scale`` ⇒ supremacy moves the split less; corners/shots
    track strength more weakly than goals, so callers pass a larger scale).
    """
    supremacy = (elo_home + home_advantage - elo_away) / scale
    lam_home = max((base_total + supremacy) / 2.0, _RATE_FLOOR)
    lam_away = max((base_total - supremacy) / 2.0, _RATE_FLOOR)
    return lam_home, lam_away


def assist_lambdas(
    lam_goal_home: float,
    lam_goal_away: float,
    *,
    assist_rate: float = 0.77,
) -> tuple[float, float]:
    """Derive per-side assist rates from modeled goal rates.

    Most goals are assisted; ``assist_rate`` (~0.77 league-typical) scales each
    side's expected goals into expected assists. This keeps assists coherent
    with the goals model rather than inventing an independent base.
    """
    return max(lam_goal_home * assist_rate, _RATE_FLOOR), max(
        lam_goal_away * assist_rate, _RATE_FLOOR
    )


# --- Poisson helpers (log-space, scipy-free, deterministic) ------------------


def poisson_pmf(lam: float, k: int) -> float:
    """``P(N == k)`` for ``N ~ Poisson(lam)``."""
    if k < 0:
        return 0.0
    return math.exp(-lam + k * math.log(lam) - math.lgamma(k + 1))


def poisson_sf(lam: float, k: int) -> float:
    """Survival ``P(N >= k)`` for ``N ~ Poisson(lam)`` (complement of the CDF)."""
    if k <= 0:
        return 1.0
    cdf = sum(poisson_pmf(lam, i) for i in range(k))
    return max(0.0, 1.0 - cdf)


def prob_count_over(lam: float, line: float) -> float:
    """``P(N > line)`` for a half-line such as 8.5 ⇒ ``P(N >= 9)``."""
    threshold = int(math.floor(line)) + 1
    return poisson_sf(lam, threshold)


def prob_count_over_under(lam: float, line: float) -> dict[str, float]:
    """``{"over", "under"}`` for a count line on rate ``lam``."""
    over = prob_count_over(lam, line)
    return {"over": over, "under": 1.0 - over}


def total_rate(lam_home: float, lam_away: float) -> float:
    """Match-total rate: the sum of two independent Poisson side-rates."""
    return lam_home + lam_away


def half_rate(lam: float, first_half_share: float = 0.45) -> float:
    """Scale a full-match rate to a first-half rate."""
    return lam * first_half_share
