"""Market taxonomy + normalized ``MarketLine`` schema for a full match surface.

A Polymarket football *game* is dozens of markets spread across sibling events
(see :mod:`fvmatch.data.polymarket.game`). This module gives them a single
normalized shape so the rest of the engine never touches raw Gamma JSON.

Each :class:`MarketLine` carries:

* ``market_type`` — a value of :class:`MarketType`, the engine's pricing key,
* ``params`` — structured line parameters (``line`` / ``side`` / ``period`` /
  ``home`` / ``away``) the pricer needs,
* ``outcomes`` — the tradeable legs (label, price, decimal odds, CLOB token id),
* provenance (``question`` / ``slug`` / ``event_id`` / ``condition_id``) and
  ``liquidity_usd`` for the gate.

The ``market_type`` deliberately separates what we can *read* from what we can
*price*: anything unrecognized maps to :attr:`MarketType.UNKNOWN` and is still
ingested (priced ``None``), never dropped.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class MarketType(str, Enum):
    """Canonical market families. Pricers dispatch on these."""

    # --- goals-derived (priced from the Dixon-Coles scoreline grid) ---
    ONE_X_TWO = "1x2"  # full-time home/draw/away moneyline
    DOUBLE_CHANCE = "double_chance"
    DRAW_NO_BET = "draw_no_bet"
    TOTAL_GOALS = "total_goals"  # over/under, params.line
    TEAM_TOTAL_GOALS = "team_total_goals"  # over/under, params.line + params.side
    BOTH_TEAMS_TO_SCORE = "btts"
    EXACT_SCORE = "exact_score"  # yes/no, params.home + params.away
    WINNING_MARGIN = "winning_margin"  # params.side + params.line (margin)
    ODD_EVEN_GOALS = "odd_even_goals"
    CLEAN_SHEET = "clean_sheet"  # params.side
    HALF_RESULT = "half_result"  # 1x2 for params.period
    HALF_TOTAL_GOALS = "half_total_goals"  # over/under, params.line + params.period

    # --- peripheral counts (priced from prior-based Poisson models) ---
    TOTAL_CORNERS = "total_corners"
    TEAM_TOTAL_CORNERS = "team_total_corners"
    HALF_TOTAL_CORNERS = "half_total_corners"
    TOTAL_SHOTS = "total_shots"
    TEAM_TOTAL_SHOTS = "team_total_shots"
    TOTAL_ASSISTS = "total_assists"
    TEAM_TOTAL_ASSISTS = "team_total_assists"

    # --- ingested but not priced (no model yet) ---
    UNKNOWN = "unknown"


#: Market types the engine can currently assign a model fair value to.
PRICEABLE: frozenset[MarketType] = frozenset(
    mt for mt in MarketType if mt is not MarketType.UNKNOWN
)

#: Market types that come from the prior-based (uncalibrated) count models.
PRIOR_BASED: frozenset[MarketType] = frozenset(
    {
        MarketType.TOTAL_CORNERS,
        MarketType.TEAM_TOTAL_CORNERS,
        MarketType.HALF_TOTAL_CORNERS,
        MarketType.TOTAL_SHOTS,
        MarketType.TEAM_TOTAL_SHOTS,
        MarketType.TOTAL_ASSISTS,
        MarketType.TEAM_TOTAL_ASSISTS,
    }
)

Period = str  # "full" | "1h" | "2h"
Side = str  # "home" | "away"


@dataclass(frozen=True)
class MarketParams:
    """Structured line parameters; only the fields a given market needs are set."""

    line: float | None = None  # totals / margin threshold (e.g. 2.5)
    side: Side | None = None  # which team (team totals, clean sheet, margin)
    period: Period = "full"  # match period for half markets
    home: int | None = None  # exact-score home goals
    away: int | None = None  # exact-score away goals


@dataclass(frozen=True)
class Outcome:
    """One tradeable leg of a market.

    ``price`` is the Polymarket cost-per-$1-share in (0, 1); ``decimal_odds`` is
    ``1 / price``. ``key`` is the canonical pricer key this leg maps to
    (e.g. ``"over"`` / ``"home"`` / ``"yes"``), filled by the parser.
    """

    label: str  # raw Polymarket outcome label ("Over", "Yes", team name…)
    price: float
    decimal_odds: float
    key: str | None = None  # canonical key for pricing (over/under/home/yes…)
    token_id: str | None = None  # CLOB token id (for execution)


@dataclass(frozen=True)
class MarketLine:
    """A normalized single market within a game's surface."""

    market_type: MarketType
    params: MarketParams
    outcomes: list[Outcome]
    question: str
    slug: str
    event_id: str | int | None = None
    condition_id: str | None = None
    liquidity_usd: float = 0.0
    raw_sports_market_type: str | None = None  # Gamma's own label, for provenance

    @property
    def is_priceable(self) -> bool:
        return self.market_type in PRICEABLE

    @property
    def is_prior_based(self) -> bool:
        return self.market_type in PRIOR_BASED


@dataclass(frozen=True)
class MarketSurface:
    """All normalized markets for one game, plus its identity."""

    home: str
    away: str
    game_id: str | int | None
    slug: str
    lines: list[MarketLine] = field(default_factory=list)

    def priceable(self) -> list[MarketLine]:
        return [m for m in self.lines if m.is_priceable]

    def by_type(self, market_type: MarketType) -> list[MarketLine]:
        return [m for m in self.lines if m.market_type is market_type]
