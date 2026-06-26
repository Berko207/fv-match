"""Tests for the per-game model context + market pricing dispatch."""

from __future__ import annotations

import math

from fvmatch.data.polymarket.taxonomy import (
    MarketLine,
    MarketParams,
    MarketType,
    Outcome,
)
from fvmatch.model.pricing import build_context, price_market


def _line(market_type: MarketType, params: MarketParams) -> MarketLine:
    return MarketLine(
        market_type=market_type,
        params=params,
        outcomes=[Outcome("Over", 0.5, 2.0), Outcome("Under", 0.5, 2.0)],
        question="synthetic",
        slug="synthetic",
    )


def _ctx():
    # Strong-ish home favourite, neutral venue
    return build_context("Mexico", "Czechia", neutral=True)


def test_context_lambdas_positive() -> None:
    ctx = _ctx()
    assert ctx.lam_home > 0 and ctx.lam_away > 0
    assert all(x > 0 for x in ctx.corner_lams)
    assert all(x > 0 for x in ctx.shots_lams)
    assert all(x > 0 for x in ctx.assist_lams)
    assert math.isclose(float(ctx.matrix.sum()), 1.0, abs_tol=1e-9)


def test_1x2_sums_to_one() -> None:
    ctx = _ctx()
    probs = price_market(_line(MarketType.ONE_X_TWO, MarketParams()), ctx)
    assert probs is not None
    assert math.isclose(sum(probs.values()), 1.0, abs_tol=1e-9)
    assert set(probs) == {"home", "draw", "away"}


def test_totals_over_under_complement() -> None:
    ctx = _ctx()
    probs = price_market(
        _line(MarketType.TOTAL_GOALS, MarketParams(line=2.5)), ctx
    )
    assert probs is not None
    assert math.isclose(probs["over"] + probs["under"], 1.0, abs_tol=1e-9)


def test_total_corners_priced_from_prior() -> None:
    ctx = _ctx()
    probs = price_market(
        _line(MarketType.TOTAL_CORNERS, MarketParams(line=9.5)), ctx
    )
    assert probs is not None
    assert math.isclose(probs["over"] + probs["under"], 1.0, abs_tol=1e-9)
    # A typical match clears 9.5 corners more often than not given base 10.5
    assert probs["over"] > 0.0


def test_half_total_fewer_than_full() -> None:
    ctx = _ctx()
    full = price_market(_line(MarketType.TOTAL_GOALS, MarketParams(line=1.5)), ctx)
    half = price_market(
        _line(MarketType.HALF_TOTAL_GOALS, MarketParams(line=1.5, period="1h")), ctx
    )
    assert full is not None and half is not None
    assert half["over"] < full["over"]


def test_team_total_corners_half_lower_rate() -> None:
    ctx = _ctx()
    full = price_market(
        _line(MarketType.TOTAL_CORNERS, MarketParams(line=4.5)), ctx
    )
    half = price_market(
        _line(MarketType.HALF_TOTAL_CORNERS, MarketParams(line=4.5, period="1h")), ctx
    )
    assert full is not None and half is not None
    assert half["over"] < full["over"]


def test_missing_param_returns_none_not_guess() -> None:
    ctx = _ctx()
    # totals with no line cannot be priced
    assert price_market(_line(MarketType.TOTAL_GOALS, MarketParams()), ctx) is None
    # clean sheet needs a side
    assert price_market(_line(MarketType.CLEAN_SHEET, MarketParams()), ctx) is None


def test_unknown_market_unpriced() -> None:
    ctx = _ctx()
    assert price_market(_line(MarketType.UNKNOWN, MarketParams()), ctx) is None


def test_exact_score_yes_no() -> None:
    ctx = _ctx()
    probs = price_market(
        _line(MarketType.EXACT_SCORE, MarketParams(home=1, away=1)), ctx
    )
    assert probs is not None
    assert math.isclose(probs["yes"] + probs["no"], 1.0, abs_tol=1e-9)
