"""Tests for Polymarket constants."""

from __future__ import annotations

from fvmatch.data.polymarket.constants import (
    CLOB_HOST,
    GAMMA_HOST,
    POLYGON_CHAIN_ID,
    PUSD_COLLATERAL,
    SignatureType,
)


def test_api_hosts() -> None:
    assert CLOB_HOST == "https://clob.polymarket.com"
    assert GAMMA_HOST == "https://gamma-api.polymarket.com"
    assert POLYGON_CHAIN_ID == 137


def test_pusd_collateral_address() -> None:
    assert PUSD_COLLATERAL.startswith("0x")
    assert len(PUSD_COLLATERAL) == 42


def test_signature_type_values() -> None:
    assert int(SignatureType.EOA) == 0
    assert int(SignatureType.POLY_1271) == 3
