"""Dixon-Coles scoreline model: fit (MLE) + predict (scoreline matrix → H/D/A).

Two complementary entry points:

* :func:`lambdas_from_elo` — turn an Elo strength difference into expected goals
  ``(lambda_home, lambda_away)``. This is the prior path used for sparse
  international fixtures (e.g. World Cup matches) where a from-scratch
  attack/defence fit is unreliable.
* :func:`fit` — full Dixon-Coles maximum-likelihood fit (attack/defence per team,
  home advantage, low-score correlation ``rho``, exponential time decay) on a set
  of historical results. Use for data-rich leagues.

Both produce ``(lambda_home, lambda_away)`` which feed :func:`scoreline_matrix`
(with the Dixon-Coles ``tau`` low-score correction) to yield the full
``P(home=i, away=j)`` grid and the marginal home/draw/away probabilities.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize

_GOAL_FLOOR = 0.02


def lambdas_from_elo(
    elo_home: float,
    elo_away: float,
    home_advantage: float = 65.0,
    base_goals: float = 2.6,
    goal_scale: float = 150.0,
) -> tuple[float, float]:
    """Map an Elo difference to expected goals for each side.

    Expected goal supremacy is ``(elo_home + home_advantage - elo_away) /
    goal_scale``; total expected goals is anchored at ``base_goals`` and split
    by that supremacy. Lambdas are floored at a small positive value so heavy
    mismatches stay well-defined.

    Args:
        elo_home, elo_away: Team Elo ratings.
        home_advantage: Elo points added to the home side (0 for neutral venues).
        base_goals: Baseline total expected goals for an even match.
        goal_scale: Elo points per 1 goal of supremacy.

    Returns:
        ``(lambda_home, lambda_away)`` expected goals.
    """
    supremacy = (elo_home + home_advantage - elo_away) / goal_scale
    lam_home = max((base_goals + supremacy) / 2.0, _GOAL_FLOOR)
    lam_away = max((base_goals - supremacy) / 2.0, _GOAL_FLOOR)
    return lam_home, lam_away


def _tau(i: int, j: int, lam_home: float, lam_away: float, rho: float) -> float:
    """Dixon-Coles low-score dependence correction factor."""
    if i == 0 and j == 0:
        return 1.0 - lam_home * lam_away * rho
    if i == 0 and j == 1:
        return 1.0 + lam_home * rho
    if i == 1 and j == 0:
        return 1.0 + lam_away * rho
    if i == 1 and j == 1:
        return 1.0 - rho
    return 1.0


def _poisson_pmf_vector(lam: float, max_goals: int) -> NDArray[np.float64]:
    """Poisson pmf for k = 0..max_goals, computed in log-space for stability."""
    ks = np.arange(max_goals + 1)
    log_pmf = -lam + ks * math.log(lam) - np.array([math.lgamma(k + 1) for k in ks])
    return np.asarray(np.exp(log_pmf), dtype=np.float64)


def scoreline_matrix(
    lam_home: float,
    lam_away: float,
    rho: float = -0.08,
    max_goals: int = 10,
) -> NDArray[np.float64]:
    """Return the normalized ``(max_goals+1, max_goals+1)`` scoreline grid.

    ``matrix[i, j] = P(home scores i, away scores j)`` with the Dixon-Coles
    ``tau`` correction applied to the four low-score cells. The grid is
    renormalized to sum to 1 (truncation at ``max_goals`` removes negligible
    tail mass).
    """
    home_pmf = _poisson_pmf_vector(lam_home, max_goals)
    away_pmf = _poisson_pmf_vector(lam_away, max_goals)
    matrix = np.outer(home_pmf, away_pmf)
    for i in (0, 1):
        for j in (0, 1):
            matrix[i, j] *= _tau(i, j, lam_home, lam_away, rho)
    matrix = np.clip(matrix, 0.0, None)
    total = matrix.sum()
    if total <= 0:
        raise ValueError("Degenerate scoreline matrix (non-positive mass)")
    return matrix / total


def marginal_hda(p_matrix: NDArray[np.float64]) -> tuple[float, float, float]:
    """Collapse a scoreline matrix into ``(p_home, p_draw, p_away)``."""
    p_home = float(np.tril(p_matrix, k=-1).sum())
    p_draw = float(np.trace(p_matrix))
    p_away = float(np.triu(p_matrix, k=1).sum())
    return p_home, p_draw, p_away


def predict_scoreline_matrix(
    home_team_id: int | str,
    away_team_id: int | str,
    params: dict[str, Any],
    max_goals: int = 10,
) -> NDArray[np.float64]:
    """Predict a scoreline matrix from fitted Dixon-Coles ``params``.

    ``params`` is the dict returned by :func:`fit`. Unknown teams fall back to a
    neutral (zero attack/defence) profile so prediction never crashes.
    """
    attack = params["attack"]
    defence = params["defence"]
    mu = params["mu"]
    gamma = params["gamma"]
    rho = params["rho"]
    home_neutral = params.get("home_advantage", True)

    a_home = attack.get(str(home_team_id), 0.0)
    a_away = attack.get(str(away_team_id), 0.0)
    d_home = defence.get(str(home_team_id), 0.0)
    d_away = defence.get(str(away_team_id), 0.0)

    home_term = gamma if home_neutral else 0.0
    lam_home = math.exp(mu + a_home - d_away + home_term)
    lam_away = math.exp(mu + a_away - d_home)
    return scoreline_matrix(lam_home, lam_away, rho=rho, max_goals=max_goals)


def _parse_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        except ValueError:
            return None
    return None


def fit(
    fixtures: list[dict[str, Any]],
    ratings: dict[int | str, float] | None = None,
    decay_lambda: float = 0.003,
    rho: float = -0.08,
    max_iter: int = 200,
) -> dict[str, Any]:
    """Fit Dixon-Coles parameters by penalized maximum likelihood.

    Each fixture dict needs ``home_team`` / ``away_team`` (names or ids) and
    integer ``home_goals`` / ``away_goals``. An optional ``kickoff_utc`` enables
    exponential time decay (recent matches weighted more, ``decay_lambda`` per
    day relative to the most recent fixture).

    Model::

        log(lambda_home) = mu + attack[home] - defence[away] + gamma
        log(lambda_away) = mu + attack[away] - defence[home]

    with ``sum(attack) = sum(defence) = 0`` for identifiability.

    Returns a params dict consumable by :func:`predict_scoreline_matrix`.
    """
    rows = [
        f
        for f in fixtures
        if f.get("home_goals") is not None and f.get("away_goals") is not None
    ]
    if not rows:
        raise ValueError("fit requires at least one fixture with final goals")

    teams = sorted(
        {str(f["home_team"]) for f in rows} | {str(f["away_team"]) for f in rows}
    )
    index = {t: i for i, t in enumerate(teams)}
    n = len(teams)

    home_idx = np.array([index[str(f["home_team"])] for f in rows])
    away_idx = np.array([index[str(f["away_team"])] for f in rows])
    home_goals = np.array([int(f["home_goals"]) for f in rows], dtype=float)
    away_goals = np.array([int(f["away_goals"]) for f in rows], dtype=float)

    dts = [_parse_dt(f.get("kickoff_utc")) for f in rows]
    if any(dt is not None for dt in dts):
        latest = max(dt for dt in dts if dt is not None)
        ages = np.array(
            [
                (latest - dt).total_seconds() / 86400.0 if dt is not None else 0.0
                for dt in dts
            ]
        )
        weights = np.exp(-decay_lambda * ages)
    else:
        weights = np.ones(len(rows))

    log_factorials = (
        np.array([math.lgamma(int(g) + 1) for g in home_goals]),
        np.array([math.lgamma(int(g) + 1) for g in away_goals]),
    )

    def neg_log_likelihood(theta: NDArray[np.float64]) -> float:
        attack = theta[:n]
        defence = theta[n : 2 * n]
        mu = theta[2 * n]
        gamma = theta[2 * n + 1]
        cur_rho = theta[2 * n + 2]

        attack = attack - attack.mean()
        defence = defence - defence.mean()

        log_lh = mu + attack[home_idx] - defence[away_idx] + gamma
        log_la = mu + attack[away_idx] - defence[home_idx]
        lam_h = np.exp(np.clip(log_lh, -10, 5))
        lam_a = np.exp(np.clip(log_la, -10, 5))

        ll_home = home_goals * np.log(lam_h) - lam_h - log_factorials[0]
        ll_away = away_goals * np.log(lam_a) - lam_a - log_factorials[1]

        tau = np.ones(len(rows))
        m00 = (home_goals == 0) & (away_goals == 0)
        m01 = (home_goals == 0) & (away_goals == 1)
        m10 = (home_goals == 1) & (away_goals == 0)
        m11 = (home_goals == 1) & (away_goals == 1)
        tau[m00] = 1.0 - lam_h[m00] * lam_a[m00] * cur_rho
        tau[m01] = 1.0 + lam_h[m01] * cur_rho
        tau[m10] = 1.0 + lam_a[m10] * cur_rho
        tau[m11] = 1.0 - cur_rho
        tau = np.clip(tau, 1e-9, None)

        ll = weights * (ll_home + ll_away + np.log(tau))
        return -float(ll.sum())

    x0 = np.concatenate([np.zeros(n), np.zeros(n), np.array([math.log(1.3), 0.2, rho])])
    bounds = (
        [(-3.0, 3.0)] * n + [(-3.0, 3.0)] * n + [(-2.0, 2.0), (-1.0, 1.0), (-0.3, 0.3)]
    )
    result = minimize(
        neg_log_likelihood,
        x0,
        method="L-BFGS-B",
        bounds=bounds,
        options={"maxiter": max_iter},
    )

    theta = result.x
    attack_arr = theta[:n] - theta[:n].mean()
    defence_arr = theta[n : 2 * n] - theta[n : 2 * n].mean()

    return {
        "model": "dixon_coles",
        "teams": teams,
        "attack": {t: float(attack_arr[index[t]]) for t in teams},
        "defence": {t: float(defence_arr[index[t]]) for t in teams},
        "mu": float(theta[2 * n]),
        "gamma": float(theta[2 * n + 1]),
        "rho": float(theta[2 * n + 2]),
        "home_advantage": True,
        "n_fixtures": len(rows),
        "converged": bool(result.success),
        "neg_log_likelihood": float(result.fun),
    }
