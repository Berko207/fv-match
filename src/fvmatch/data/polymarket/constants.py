"""Polymarket CLOB V2 constants — URLs, chain, collateral, redemption adapters."""

from __future__ import annotations

from enum import IntEnum

# API hosts (global crypto-native CLOB V2 — not polymarket.us)
CLOB_HOST = "https://clob.polymarket.com"
GAMMA_HOST = "https://gamma-api.polymarket.com"
DATA_API_HOST = "https://data-api.polymarket.com"

POLYGON_CHAIN_ID = 137

# pUSD collateral (Polygon mainnet)
PUSD_COLLATERAL = "0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB"
COLLATERAL_ONRAMP = "0x93070a847efEf7F70739046A929D47a521F5B8ee"
COLLATERAL_OFFRAMP = "0x2957922Eb93258b93368531d39fAcCA3B4dC5854"
USDC_E_POLYGON = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"

# CTF Exchange V2 (EIP-712 domain version "2")
CTF_EXCHANGE = "0xE111180000d2663C0091e4f400237545B87B996B"
NEG_RISK_CTF_EXCHANGE = "0xe2222d279d744050d28e00520010520000310F59"

# Redemption adapters (pUSD output)
CTF_COLLATERAL_ADAPTER = "0xAdA100Db00Ca00073811820692005400218FcE1f"
NEG_RISK_CTF_COLLATERAL_ADAPTER = "0xadA2005600Dec949baf300f4C6120000bDB6eAab"


class SignatureType(IntEnum):
    """ClobClient signature_type values for V2."""

    EOA = 0
    POLY_PROXY = 1
    GNOSIS_SAFE = 2
    POLY_1271 = 3  # deposit wallet — verify SDK release notes before use in Python
