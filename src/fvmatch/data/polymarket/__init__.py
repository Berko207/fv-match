"""Polymarket Gamma + CLOB V2 read clients (global crypto-native stack, chain 137)."""

from fvmatch.data.polymarket.clob_read import ClobReadClient
from fvmatch.data.polymarket.constants import (
    CLOB_HOST,
    DATA_API_HOST,
    GAMMA_HOST,
    SignatureType,
)
from fvmatch.data.polymarket.gamma import GammaClient, GammaMarket
from fvmatch.data.polymarket.odds import (
    MatchOdds,
    fetch_event_by_slug,
    fetch_market_by_slug,
    fetch_match_odds,
    fetch_three_way_odds,
    parse_match_odds,
    parse_three_way_odds,
    search_events,
)

__all__ = [
    "CLOB_HOST",
    "ClobReadClient",
    "DATA_API_HOST",
    "GAMMA_HOST",
    "GammaClient",
    "GammaMarket",
    "MatchOdds",
    "SignatureType",
    "fetch_event_by_slug",
    "fetch_market_by_slug",
    "fetch_match_odds",
    "fetch_three_way_odds",
    "parse_match_odds",
    "parse_three_way_odds",
    "search_events",
]
