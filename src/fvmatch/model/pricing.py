"""Pricing dispatch: one model context per game → fair value for every market type.

:func:`build_context` computes — once per fixture — the Dixon-Coles scoreline
grid, its first-half approximation, and the prior-based corner/shot/assist Poisson
rates. :func:`price_market` then maps any :class:`~fvmatch.data.polymarket.taxonomy.MarketLine`
to canonical-keyed model probabilities (e.g. ``{"over": .., "under": ..}``) by
dispatching on its :class:`~fvmatch.data.polymarket.taxonomy.MarketType`.

Unpriceable markets (``MarketType.UNKNOWN``) return ``None`` — they are still
carried through the surface as read-only signals.

Canonical keys by family::

    1x2 / half_result         -> {"home", "draw", "away"}
    double_chance             -> {"1X", "12", "X2"}
    draw_no_bet               -> {"home", "away"}
    *_total_* / *_over_under  -> {"over", "under"}
    btts / clean_sheet /
      exact_score / margin    -> {"yes", "no"}
    odd_even_goals            -> {"odd", "even"}
"""

from __future__ import annotations

from dataclasses import dataclass

from numpy.typing import NDArray

from fvmatch.config import Settings
from fvmatch.config import settings as default_settings
from fvmatch.data.polymarket.taxonomy import MarketLine, MarketType
from fvmatch.model import counts, markets
from fvmatch.model.dixon_coles import lambdas_from_elo, scoreline_matrix
from fvmatch.model.ratings_prior import get_rating

Matrix = NDArray


@dataclass(frozen=True)
class ModelContext:
    """Everything the pricers need for one fixture, computed once."""

    matrix: Matrix  # full-match scoreline grid
    half_matrix: Matrix  # first-half scoreline grid (approx)
    lam_home: float  # expected home goals
    lam_away: float  # expected away goals
    corner_lams: tuple[float, float]
    shots_lams: tuple[float, float]
    assist_lams: tuple[float, float]


def build_context(
    home: str,
    away: str,
    *,
    neutral: bool = True,
    elo_home: float | None = None,
    elo_away: float | None = None,
    config: Settings | None = None,
) -> ModelContext:
    """Build the per-fixture model context from Elo ratings."""
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
    half_matrix = markets.first_half_matrix(
        lam_home,
        lam_away,
        first_half_goal_share=cfg.first_half_goal_share,
        rho=cfg.dc_rho,
        max_goals=cfg.max_goals,
    )
    corner_lams = counts.count_lambdas(
        eh, ea, cfg.base_corners, scale=cfg.corner_elo_scale, home_advantage=home_adv
    )
    shots_lams = counts.count_lambdas(
        eh, ea, cfg.base_shots, scale=cfg.shots_elo_scale, home_advantage=home_adv
    )
    assist_lams = counts.assist_lambdas(
        lam_home, lam_away, assist_rate=cfg.assist_rate
    )
    return ModelContext(
        matrix=matrix,
        half_matrix=half_matrix,
        lam_home=lam_home,
        lam_away=lam_away,
        corner_lams=corner_lams,
        shots_lams=shots_lams,
        assist_lams=assist_lams,
    )


def _yes_no(p: float) -> dict[str, float]:
    return {"yes": p, "no": 1.0 - p}


def _count_rate(
    ctx: ModelContext, lams: tuple[float, float], line: MarketLine
) -> float:
    """Resolve the Poisson rate for a count market: team / half / full-match total."""
    home_rate, away_rate = lams
    side = line.params.side
    if side == "home":
        rate = home_rate
    elif side == "away":
        rate = away_rate
    else:
        rate = counts.total_rate(home_rate, away_rate)
    if line.params.period in ("1h", "2h"):
        share = (
            default_settings.first_half_goal_share
            if line.params.period == "1h"
            else 1.0 - default_settings.first_half_goal_share
        )
        rate = counts.half_rate(rate, share)
    return rate


def price_market(line: MarketLine, ctx: ModelContext) -> dict[str, float] | None:
    """Model probabilities for ``line`` keyed by canonical outcome, or ``None``.

    ``None`` means the market type has no pricer (read-only signal). A pricer
    that needs a missing parameter (e.g. a totals line) also returns ``None``
    rather than guessing.
    """
    mt = line.market_type
    p = line.params
    m = ctx.matrix
    hm = ctx.half_matrix

    # --- goals-derived ---
    if mt is MarketType.ONE_X_TWO:
        h, d, a = markets.prob_hda(m)
        return {"home": h, "draw": d, "away": a}
    if mt is MarketType.HALF_RESULT:
        h, d, a = markets.prob_hda(hm)
        return {"home": h, "draw": d, "away": a}
    if mt is MarketType.DOUBLE_CHANCE:
        return markets.prob_double_chance(m)
    if mt is MarketType.DRAW_NO_BET:
        return markets.prob_draw_no_bet(m)
    if mt is MarketType.BOTH_TEAMS_TO_SCORE:
        return markets.prob_both_teams_to_score(m)
    if mt is MarketType.ODD_EVEN_GOALS:
        return markets.prob_odd_even_total(m)
    if mt is MarketType.CLEAN_SHEET:
        if p.side not in ("home", "away"):
            return None
        return markets.prob_clean_sheet(m, p.side)
    if mt is MarketType.EXACT_SCORE:
        if p.home is None or p.away is None:
            return None
        return _yes_no(markets.prob_exact_score(m, p.home, p.away))
    if mt is MarketType.WINNING_MARGIN:
        if p.line is None or p.side not in ("home", "away"):
            return None
        return _yes_no(markets.prob_winning_margin(m, int(p.line), p.side))
    if mt is MarketType.TOTAL_GOALS:
        if p.line is None:
            return None
        return markets.prob_total_over_under(m, p.line)
    if mt is MarketType.TEAM_TOTAL_GOALS:
        if p.line is None or p.side not in ("home", "away"):
            return None
        return markets.prob_team_total_over_under(m, p.line, p.side)
    if mt is MarketType.HALF_TOTAL_GOALS:
        if p.line is None:
            return None
        return markets.prob_total_over_under(hm, p.line)

    # --- peripheral counts (prior-based) ---
    if mt in (
        MarketType.TOTAL_CORNERS,
        MarketType.TEAM_TOTAL_CORNERS,
        MarketType.HALF_TOTAL_CORNERS,
    ):
        if p.line is None:
            return None
        return counts.prob_count_over_under(_count_rate(ctx, ctx.corner_lams, line), p.line)
    if mt in (MarketType.TOTAL_SHOTS, MarketType.TEAM_TOTAL_SHOTS):
        if p.line is None:
            return None
        return counts.prob_count_over_under(_count_rate(ctx, ctx.shots_lams, line), p.line)
    if mt in (MarketType.TOTAL_ASSISTS, MarketType.TEAM_TOTAL_ASSISTS):
        if p.line is None:
            return None
        return counts.prob_count_over_under(_count_rate(ctx, ctx.assist_lams, line), p.line)

    return None  # UNKNOWN / unpriceable
