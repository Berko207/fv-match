"""End-to-end fair-value engine: team strength → model probs → market edge.

This is the glue that makes ``fvmatch`` a usable tool. Given two teams and
(optionally) the three-way match odds, it produces:

* model home/draw/away probabilities from a Dixon-Coles scoreline matrix whose
  goal expectations come from the Elo strength prior,
* the de-vigged market consensus and the per-outcome edge,
* fractional-Kelly stake sizing on the price actually paid, gated by the edge
  threshold.

Everything here is pure/deterministic given its inputs (no network, no DB), so
it runs anywhere and is fully testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

import numpy as np
from numpy.typing import NDArray

from fvmatch.config import Settings
from fvmatch.config import settings as default_settings
from fvmatch.edge.devig import Method, devig
from fvmatch.edge.gate import filter_legs
from fvmatch.edge.kelly import Leg, joint_match_stakes
from fvmatch.model.dixon_coles import (
    lambdas_from_elo,
    marginal_hda,
    scoreline_matrix,
)
from fvmatch.model.ratings_prior import get_rating

OUTCOMES = ("home", "draw", "away")


@dataclass(frozen=True)
class OutcomeView:
    outcome: str
    model_p: float
    fair_odds: float
    market_price: float | None  # cost per $1 share = 1/decimal_odds
    market_odds: float | None
    consensus_p: float | None  # de-vigged market probability
    edge: float | None  # model_p - consensus_p
    ev_per_dollar: float | None  # model_p / market_price - 1
    stake_fraction: float
    stake_usd: float
    bet: bool


@dataclass(frozen=True)
class MatchAnalysis:
    home: str
    away: str
    neutral: bool
    elo_home: float
    elo_away: float
    lam_home: float
    lam_away: float
    p_home: float
    p_draw: float
    p_away: float
    expected_home_goals: float
    expected_away_goals: float
    overround: float | None
    outcomes: list[OutcomeView]
    top_scorelines: list[tuple[int, int, float]] = field(default_factory=list)
    dry_run: bool = True

    @property
    def has_bets(self) -> bool:
        return any(o.bet for o in self.outcomes)


def _top_scorelines(
    matrix: NDArray[np.float64], n: int = 6
) -> list[tuple[int, int, float]]:
    flat: list[tuple[int, int, float]] = []
    rows, cols = matrix.shape
    for i in range(rows):
        for j in range(cols):
            flat.append((i, j, float(matrix[i, j])))
    flat.sort(key=lambda t: t[2], reverse=True)
    return flat[:n]


def analyze_match(
    home: str,
    away: str,
    home_odds: float | None = None,
    draw_odds: float | None = None,
    away_odds: float | None = None,
    *,
    neutral: bool = True,
    elo_home: float | None = None,
    elo_away: float | None = None,
    config: Settings | None = None,
    devig_method: Method | None = None,
) -> MatchAnalysis:
    """Run the full fair-value pipeline for a single fixture.

    Args:
        home, away: Team names (looked up in the bundled Elo seed).
        home_odds, draw_odds, away_odds: Decimal odds for the three-way market.
            If omitted, the analysis is model-only (no edge/stakes).
        neutral: True for a neutral venue (no home-advantage Elo bump).
        elo_home, elo_away: Override the looked-up Elo ratings.
        config: Settings instance (defaults to the global ``settings``).
        devig_method: Override the configured de-vig method.

    Returns:
        A populated :class:`MatchAnalysis`.
    """
    cfg = config or default_settings
    eh = elo_home if elo_home is not None else get_rating(home)
    ea = elo_away if elo_away is not None else get_rating(away)
    home_adv = 0.0 if neutral else cfg.home_advantage_elo

    lam_home, lam_away = lambdas_from_elo(
        eh,
        ea,
        home_advantage=home_adv,
        base_goals=cfg.base_goals,
        goal_scale=cfg.elo_goal_scale,
    )
    matrix = scoreline_matrix(
        lam_home, lam_away, rho=cfg.dc_rho, max_goals=cfg.max_goals
    )
    p_home, p_draw, p_away = marginal_hda(matrix)
    model_ps = {"home": p_home, "draw": p_draw, "away": p_away}

    have_odds = (
        home_odds is not None
        and draw_odds is not None
        and away_odds is not None
        and home_odds > 1.0
        and draw_odds > 1.0
        and away_odds > 1.0
    )

    odds_map: dict[str, float] = {}
    consensus: dict[str, float] = {}
    overround: float | None = None
    legs: list[Leg] = []
    if have_odds:
        odds_map = {
            "home": float(home_odds),  # type: ignore[arg-type]
            "draw": float(draw_odds),  # type: ignore[arg-type]
            "away": float(away_odds),  # type: ignore[arg-type]
        }
        ordered = [odds_map[o] for o in OUTCOMES]
        method = cast(Method, devig_method or cfg.devig_method)
        devigged = devig(ordered, method=method)
        consensus = dict(zip(OUTCOMES, devigged, strict=True))
        overround = sum(1.0 / o for o in ordered) - 1.0
        for o in OUTCOMES:
            legs.append(Leg(outcome=o, p=model_ps[o], price=1.0 / odds_map[o]))

    kept = filter_legs(legs, threshold=cfg.edge_threshold) if have_odds else []
    stake_fracs = (
        joint_match_stakes(kept, fraction=cfg.kelly_fraction, cap=cfg.kelly_cap)
        if kept
        else []
    )
    stake_by_outcome = {
        leg.outcome: frac for leg, frac in zip(kept, stake_fracs, strict=True)
    }

    views: list[OutcomeView] = []
    for o in OUTCOMES:
        mp = model_ps[o]
        if have_odds:
            odds = odds_map[o]
            price = 1.0 / odds
            cons = consensus[o]
            edge = mp - cons
            ev = mp / price - 1.0
            frac = stake_by_outcome.get(o, 0.0)
            views.append(
                OutcomeView(
                    outcome=o,
                    model_p=mp,
                    fair_odds=1.0 / mp if mp > 0 else float("inf"),
                    market_price=price,
                    market_odds=odds,
                    consensus_p=cons,
                    edge=edge,
                    ev_per_dollar=ev,
                    stake_fraction=frac,
                    stake_usd=frac * cfg.bankroll,
                    bet=frac > 0.0,
                )
            )
        else:
            views.append(
                OutcomeView(
                    outcome=o,
                    model_p=mp,
                    fair_odds=1.0 / mp if mp > 0 else float("inf"),
                    market_price=None,
                    market_odds=None,
                    consensus_p=None,
                    edge=None,
                    ev_per_dollar=None,
                    stake_fraction=0.0,
                    stake_usd=0.0,
                    bet=False,
                )
            )

    return MatchAnalysis(
        home=home,
        away=away,
        neutral=neutral,
        elo_home=eh,
        elo_away=ea,
        lam_home=lam_home,
        lam_away=lam_away,
        p_home=p_home,
        p_draw=p_draw,
        p_away=p_away,
        expected_home_goals=lam_home,
        expected_away_goals=lam_away,
        overround=overround,
        outcomes=views,
        top_scorelines=_top_scorelines(matrix),
        dry_run=cfg.dry_run,
    )
