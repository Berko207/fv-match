"""Tests for Polymarket Gamma client parsing."""

from __future__ import annotations

from fvmatch.data.polymarket.gamma import _parse_gamma_market

SAMPLE_MARKET = {
    "id": "12345",
    "question": "Will Team A beat Team B?",
    "conditionId": "0xabc",
    "slug": "team-a-vs-team-b",
    "outcomes": '["Home", "Draw", "Away"]',
    "outcomePrices": '["0.45", "0.28", "0.27"]',
    "clobTokenIds": '["111", "222", "333"]',
    "negRisk": True,
    "orderPriceMinTickSize": 0.01,
    "orderMinSize": 5,
    "active": True,
    "closed": False,
    "liquidityNum": 12000.5,
    "volumeNum": 500000.0,
}


def test_parse_gamma_market_outcomes_and_tokens() -> None:
    market = _parse_gamma_market(SAMPLE_MARKET)
    assert market.outcomes == ("Home", "Draw", "Away")
    assert market.outcome_prices == (0.45, 0.28, 0.27)
    assert market.clob_token_ids == ("111", "222", "333")
    assert market.neg_risk is True
    assert market.tick_size == "0.01"
    assert market.liquidity_usd == 12000.5


def test_token_id_for_outcome_case_insensitive() -> None:
    market = _parse_gamma_market(SAMPLE_MARKET)
    assert market.token_id_for_outcome("home") == "111"
    assert market.token_id_for_outcome("AWAY") == "333"
    assert market.token_id_for_outcome("unknown") is None


def test_price_for_outcome() -> None:
    market = _parse_gamma_market(SAMPLE_MARKET)
    assert market.price_for_outcome("draw") == 0.28
    assert market.price_for_outcome("missing") is None
