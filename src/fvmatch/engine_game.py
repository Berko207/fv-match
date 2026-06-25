"""Whole-game fair-value engine: a MarketSurface → edges across every market.

Where :func:`fvmatch.engine.analyze_match` prices a single 1X2 market, this
prices the *entire surface* of a game — totals, BTTS, exact scores, team totals,
halves, corners, shots, assists — against one model context, and surfaces the
+EV opportunities ranked across all of them.

Risk model:

* Each outcome is gated independently on ``model_p - market_price > edge_threshold``
  and on the market's liquidity.
* Stakes are fractional Kelly on the price actually paid, then a single global
  proportional scale caps **total game exposure** at ``kelly_cap`` of bankroll —
  the whole game is treated as one match for exposure, which is conservative
  given markets within a game are correlated (true joint Kelly is future work).

Output is a :class:`GameAnalysis` whose :meth:`GameAnalysis.to_dict` is the
structured, agent-consumable signal: every market with its model fair value (or
``null`` when unpriceable), market price, edge, and dry-run stake.

Strictly DRY_RUN: this proposes stakes and never places an order. Per the repo
invariant, live execution additionally requires ``DRY_RUN=false`` AND a passed
positive-CLV validation gate. Prior-based markets (corners/shots/assists) are
flagged ``prior_based`` — treat their edges as uncalibrated hypotheses.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import cast

from fvmatch.config import Settings
from fvmatch.config import settings as default_settings
from fvmatch.data.polymarket.taxonomy import MarketLine, MarketSurface
from fvmatch.edge.devig import Method, devig
from fvmatch.edge.kelly import Leg, kelly_fraction
from fvmatch.model.pricing import ModelContext, build_context, price_market
from fvmatch.model.ratings_prior import get_rating


@dataclass(frozen=True)
class MarketOutcomeView:
    label: str
    key: str | None
    model_p: float | None
    market_price: float | None
    market_odds: float | None
    consensus_p: float | None
    edge: float | None
    ev_per_dollar: float | None
    stake_fraction: float
    stake_usd: float
    bet: bool
    token_id: str | None


@dataclass(frozen=True)
class MarketView:
    market_type: str
    question: str
    slug: str
    period: str
    line: float | None
    side: str | None
    priceable: bool
    prior_based: bool
    liquidity_usd: float
    overround: float | None
    outcomes: list[MarketOutcomeView]

    @property
    def has_bet(self) -> bool:
        return any(o.bet for o in self.outcomes)


@dataclass(frozen=True)
class ProposedBet:
    market_type: str
    question: str
    outcome: str
    model_p: float
    market_price: float
    market_odds: float
    edge: float
    ev_per_dollar: float
    stake_usd: float
    prior_based: bool
    token_id: str | None


@dataclass(frozen=True)
class GameAnalysis:
    home: str
    away: str
    slug: str
    game_id: str | int | None
    neutral: bool
    elo_home: float
    elo_away: float
    expected_home_goals: float
    expected_away_goals: float
    n_markets: int
    n_priceable: int
    markets: list[MarketView]
    proposed_bets: list[ProposedBet]
    dry_run: bool = True

    @property
    def total_stake_usd(self) -> float:
        return sum(b.stake_usd for b in self.proposed_bets)

    def to_dict(self) -> dict:
        """JSON-ready structure — the signal an agent consumes."""
        return {
            "home": self.home,
            "away": self.away,
            "slug": self.slug,
            "game_id": self.game_id,
            "neutral": self.neutral,
            "elo": {"home": self.elo_home, "away": self.elo_away},
            "expected_goals": {
                "home": self.expected_home_goals,
                "away": self.expected_away_goals,
            },
            "n_markets": self.n_markets,
            "n_priceable": self.n_priceable,
            "dry_run": self.dry_run,
            "total_stake_usd": self.total_stake_usd,
            "proposed_bets": [asdict(b) for b in self.proposed_bets],
            "markets": [
                {
                    "market_type": m.market_type,
                    "question": m.question,
                    "slug": m.slug,
                    "period": m.period,
                    "line": m.line,
                    "side": m.side,
                    "priceable": m.priceable,
                    "prior_based": m.prior_based,
                    "liquidity_usd": m.liquidity_usd,
                    "overround": m.overround,
                    "outcomes": [asdict(o) for o in m.outcomes],
                }
                for m in self.markets
            ],
        }


@dataclass
class _Candidate:
    """A gated leg awaiting global stake sizing."""

    market_idx: int
    outcome_idx: int
    leg: Leg
    consensus_p: float | None
    liquidity_usd: float


def _price_one_market(
    line: MarketLine,
    ctx: ModelContext,
    method: Method,
) -> tuple[
    list[MarketOutcomeView], float | None, dict[int, tuple[Leg, float | None]]
]:
    """Build outcome views for one market and return its candidate legs.

    Returns ``(views, overround, candidates_by_outcome_idx)`` where each
    candidate maps outcome index → ``(Leg, consensus_p)``; staking/gating is
    applied globally by the caller.
    """
    model_probs = price_market(line, ctx)
    priceable = model_probs is not None

    # outcomes that carry a usable price (for de-vig / overround)
    priced_idx = [
        i
        for i, o in enumerate(line.outcomes)
        if o.decimal_odds > 1.0 and o.price > 0.0
    ]
    overround: float | None = None
    consensus: dict[int, float] = {}
    if len(priced_idx) >= 2:
        odds = [line.outcomes[i].decimal_odds for i in priced_idx]
        overround = sum(1.0 / o for o in odds) - 1.0
        devigged = devig(odds, method=method)
        consensus = dict(zip(priced_idx, devigged, strict=True))

    views: list[MarketOutcomeView] = []
    candidates: dict[int, tuple[Leg, float | None]] = {}
    for i, o in enumerate(line.outcomes):
        mp = model_probs.get(o.key) if (priceable and o.key) else None
        has_price = o.decimal_odds > 1.0 and o.price > 0.0
        cons = consensus.get(i)
        if mp is not None and has_price:
            edge = mp - (cons if cons is not None else o.price)
            ev = mp / o.price - 1.0
            candidates[i] = (Leg(outcome=o.key or "", p=mp, price=o.price), cons)
        else:
            edge = None
            ev = None
        views.append(
            MarketOutcomeView(
                label=o.label,
                key=o.key,
                model_p=mp,
                market_price=o.price if has_price else None,
                market_odds=o.decimal_odds if has_price else None,
                consensus_p=cons,
                edge=edge,
                ev_per_dollar=ev,
                stake_fraction=0.0,
                stake_usd=0.0,
                bet=False,
                token_id=o.token_id,
            )
        )
    return views, overround, candidates


def analyze_game(
    surface: MarketSurface,
    *,
    neutral: bool = True,
    elo_home: float | None = None,
    elo_away: float | None = None,
    config: Settings | None = None,
    devig_method: Method | None = None,
) -> GameAnalysis:
    """Price every market in ``surface`` and size +EV bets under a game cap."""
    cfg = config or default_settings
    eh = elo_home if elo_home is not None else get_rating(surface.home)
    ea = elo_away if elo_away is not None else get_rating(surface.away)
    ctx = build_context(
        surface.home,
        surface.away,
        neutral=neutral,
        elo_home=eh,
        elo_away=ea,
        config=cfg,
    )
    method = cast(Method, devig_method or cfg.devig_method)

    market_views: list[list[MarketOutcomeView]] = []
    overrounds: list[float | None] = []
    candidates: list[_Candidate] = []

    for mi, line in enumerate(surface.lines):
        views, overround, cand = _price_one_market(line, ctx, method)
        market_views.append(views)
        overrounds.append(overround)
        for oi, (leg, cons) in cand.items():
            # edge gate + liquidity gate
            if (leg.p - leg.price) <= cfg.edge_threshold:
                continue
            if line.liquidity_usd and line.liquidity_usd < cfg.min_liquidity_usd:
                continue
            candidates.append(
                _Candidate(
                    market_idx=mi,
                    outcome_idx=oi,
                    leg=leg,
                    consensus_p=cons,
                    liquidity_usd=line.liquidity_usd,
                )
            )

    # global fractional Kelly with a single proportional scale to the game cap
    raw = [
        kelly_fraction(c.leg.p, c.leg.price) * cfg.kelly_fraction for c in candidates
    ]
    total = sum(raw)
    scale = (cfg.kelly_cap / total) if total > cfg.kelly_cap and total > 0 else 1.0
    fractions = [r * scale for r in raw]

    proposed: list[ProposedBet] = []
    for c, frac in zip(candidates, fractions, strict=True):
        if frac <= 0:
            continue
        stake_usd = frac * cfg.bankroll
        view = market_views[c.market_idx][c.outcome_idx]
        market_views[c.market_idx][c.outcome_idx] = MarketOutcomeView(
            **{
                **asdict(view),
                "stake_fraction": frac,
                "stake_usd": stake_usd,
                "bet": True,
            }
        )
        line = surface.lines[c.market_idx]
        proposed.append(
            ProposedBet(
                market_type=line.market_type.value,
                question=line.question,
                outcome=c.leg.outcome,
                model_p=c.leg.p,
                market_price=c.leg.price,
                market_odds=1.0 / c.leg.price if c.leg.price > 0 else float("inf"),
                edge=c.leg.p - (c.consensus_p if c.consensus_p is not None else c.leg.price),
                ev_per_dollar=c.leg.p / c.leg.price - 1.0,
                stake_usd=stake_usd,
                prior_based=line.is_prior_based,
                token_id=surface.lines[c.market_idx].outcomes[c.outcome_idx].token_id,
            )
        )

    proposed.sort(key=lambda b: b.ev_per_dollar, reverse=True)

    views_out: list[MarketView] = []
    for mi, line in enumerate(surface.lines):
        views_out.append(
            MarketView(
                market_type=line.market_type.value,
                question=line.question,
                slug=line.slug,
                period=line.params.period,
                line=line.params.line,
                side=line.params.side,
                priceable=line.is_priceable,
                prior_based=line.is_prior_based,
                liquidity_usd=line.liquidity_usd,
                overround=overrounds[mi],
                outcomes=market_views[mi],
            )
        )

    return GameAnalysis(
        home=surface.home,
        away=surface.away,
        slug=surface.slug,
        game_id=surface.game_id,
        neutral=neutral,
        elo_home=eh,
        elo_away=ea,
        expected_home_goals=ctx.lam_home,
        expected_away_goals=ctx.lam_away,
        n_markets=len(surface.lines),
        n_priceable=sum(1 for line in surface.lines if line.is_priceable),
        markets=views_out,
        proposed_bets=proposed,
        dry_run=cfg.dry_run,
    )
