"""Deterministic tests for the Polymarket cross-market 3-way reader (no network).

A football match on Polymarket is one *event* holding three separate Yes/No
markets (home win / draw / away win); the ``Yes`` prices are the H/D/A implied
probabilities. These tests cover assembling those into decimal odds.
"""

from __future__ import annotations

import pytest

from fvmatch.data.polymarket import MatchOdds, parse_match_odds


def _market(
    slug: str, question: str, yes: float, no: float, liq: float, closed: bool = False
) -> dict:
    # outcomePrices come back from Gamma as JSON-encoded strings.
    return {
        "slug": slug,
        "question": question,
        "outcomes": '["Yes", "No"]',
        "outcomePrices": f'["{yes}", "{no}"]',
        "liquidityNum": liq,
        "closed": closed,
    }


def _event(
    markets: list[dict] | None = None, title: str = "Colombia vs. DR Congo"
) -> dict:
    if markets is None:
        markets = [
            _market(
                "fifwc-col-cdr-2026-06-23-draw",
                "Will Colombia vs. DR Congo end in a draw?",
                0.315,
                0.685,
                2_383_272.0,
            ),
            _market(
                "fifwc-col-cdr-2026-06-23-col",
                "Will Colombia win on 2026-06-23?",
                0.585,
                0.415,
                2_317_297.0,
            ),
            _market(
                "fifwc-col-cdr-2026-06-23-cdr",
                "Will DR Congo win on 2026-06-23?",
                0.095,
                0.905,
                2_414_751.0,
            ),
        ]
    return {"title": title, "markets": markets}


def test_parse_match_odds_assembles_three_way() -> None:
    odds = parse_match_odds(_event(), "Colombia", "DR Congo")
    assert isinstance(odds, MatchOdds)
    assert odds.home_team == "Colombia" and odds.away_team == "DR Congo"
    assert odds.home_odds == pytest.approx(1.0 / 0.585, rel=1e-9)
    assert odds.draw_odds == pytest.approx(1.0 / 0.315, rel=1e-9)
    assert odds.away_odds == pytest.approx(1.0 / 0.095, rel=1e-9)
    # Liquidity gate uses the thinnest leg.
    assert odds.min_liquidity_usd == pytest.approx(2_317_297.0)


def test_draw_leg_classified_first_despite_both_team_names() -> None:
    # The draw question contains BOTH team names; it must not be read as home/away.
    odds = parse_match_odds(_event(), "Colombia", "DR Congo")
    assert odds is not None
    # If the draw had been misread as the home leg, home_odds would equal 1/0.315.
    assert odds.home_odds == pytest.approx(1.0 / 0.585, rel=1e-9)


def test_team_names_derived_from_title_when_not_supplied() -> None:
    odds = parse_match_odds(_event())  # no explicit home/away
    assert odds is not None
    assert odds.home_team == "Colombia" and odds.away_team == "DR Congo"
    assert odds.away_odds == pytest.approx(1.0 / 0.095, rel=1e-9)


def test_prices_as_native_lists_also_parse() -> None:
    markets = _event()["markets"]
    for m in markets:
        m["outcomes"] = ["Yes", "No"]
    odds = parse_match_odds(
        {"title": "Colombia vs. DR Congo", "markets": markets}, "Colombia", "DR Congo"
    )
    assert odds is not None and odds.home_odds == pytest.approx(1.0 / 0.585, rel=1e-9)


def test_missing_leg_returns_none() -> None:
    two_legs = _event()["markets"][:2]  # draw + home only
    assert (
        parse_match_odds(
            {"title": "Colombia vs. DR Congo", "markets": two_legs},
            "Colombia",
            "DR Congo",
        )
        is None
    )


def test_closed_leg_is_skipped() -> None:
    markets = _event()["markets"]
    markets[2]["closed"] = True  # close the away leg
    assert (
        parse_match_odds(
            {"title": "Colombia vs. DR Congo", "markets": markets},
            "Colombia",
            "DR Congo",
        )
        is None
    )


def test_untitled_event_without_names_returns_none() -> None:
    assert parse_match_odds({"markets": _event()["markets"]}) is None


def test_zero_or_bad_price_leg_returns_none() -> None:
    markets = _event()["markets"]
    markets[1] = _market(
        "fifwc-col-cdr-2026-06-23-col",
        "Will Colombia win on 2026-06-23?",
        0.0,
        1.0,
        1.0,
    )
    assert (
        parse_match_odds(
            {"title": "Colombia vs. DR Congo", "markets": markets},
            "Colombia",
            "DR Congo",
        )
        is None
    )
