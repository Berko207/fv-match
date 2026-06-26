"""Tests for the Polymarket market classifier (question/slug -> MarketType).

Question strings are seeded from the observed CZE-MEX surface (combos panel +
captured 3-way legs). These lock the heuristics; extend as real shapes land.
"""

from __future__ import annotations

from fvmatch.data.polymarket.classify import classify_market
from fvmatch.data.polymarket.taxonomy import MarketType, Outcome

HOME, AWAY = "Czechia", "Mexico"


def _ou() -> list[Outcome]:
    return [Outcome("Over", 0.5, 2.0), Outcome("Under", 0.5, 2.0)]


def _yn() -> list[Outcome]:
    return [Outcome("Yes", 0.5, 2.0), Outcome("No", 0.5, 2.0)]


def _c(question: str, outcomes, slug: str = ""):
    return classify_market(question, slug or question, outcomes, HOME, AWAY)


def test_total_goals() -> None:
    line = _c("Total goals Over/Under 2.5", _ou())
    assert line.market_type is MarketType.TOTAL_GOALS
    assert line.params.line == 2.5
    assert {o.key for o in line.outcomes} == {"over", "under"}


def test_total_corners() -> None:
    line = _c("Total Corners Over 8.5", _ou())
    assert line.market_type is MarketType.TOTAL_CORNERS
    assert line.params.line == 8.5


def test_first_half_corners_period_and_type() -> None:
    line = _c("1st Half Corners Over 4.5", _ou())
    assert line.market_type is MarketType.HALF_TOTAL_CORNERS
    assert line.params.period == "1h"
    assert line.params.line == 4.5


def test_first_half_total_goals() -> None:
    line = _c("1st Half Total Over 0.5", _ou())
    assert line.market_type is MarketType.HALF_TOTAL_GOALS
    assert line.params.period == "1h"
    assert line.params.line == 0.5


def test_both_teams_to_score() -> None:
    line = _c("Both Teams to Score", _yn())
    assert line.market_type is MarketType.BOTH_TEAMS_TO_SCORE
    assert {o.key for o in line.outcomes} == {"yes", "no"}


def test_exact_score_parses_goals() -> None:
    line = _c("Exact Score Czechia 0-1 Mexico", _yn())
    assert line.market_type is MarketType.EXACT_SCORE
    assert line.params.home == 0
    assert line.params.away == 1


def test_team_total_goals_side() -> None:
    line = _c("Mexico Total Goals Over 1.5", _ou())
    assert line.market_type is MarketType.TEAM_TOTAL_GOALS
    assert line.params.side == "away"  # Mexico is the away/second team here
    assert line.params.line == 1.5


def test_team_total_shots() -> None:
    line = _c("Czechia Total Shots Over 9.5", _ou())
    assert line.market_type is MarketType.TEAM_TOTAL_SHOTS
    assert line.params.side == "home"


def test_total_assists() -> None:
    line = _c("Total Assists Over 1.5", _ou())
    assert line.market_type is MarketType.TOTAL_ASSISTS
    assert line.params.line == 1.5


def test_clean_sheet_side() -> None:
    line = _c("Mexico Clean Sheet", _yn())
    assert line.market_type is MarketType.CLEAN_SHEET
    assert line.params.side == "away"


def test_iso_date_not_mistaken_for_scoreline() -> None:
    # A win leg's question carries the date; must NOT become an exact score
    line = _c("Will Mexico win on 2026-06-24?", _yn(), slug="fifwc-mex-win")
    assert line.market_type is not MarketType.EXACT_SCORE


def test_unrecognized_is_unknown_not_dropped() -> None:
    line = _c("Will there be a VAR review in the match?", _yn())
    assert line.market_type is MarketType.UNKNOWN
    assert line.is_priceable is False
