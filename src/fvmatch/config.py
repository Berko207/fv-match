"""Pydantic-settings driven configuration. All secrets via env; defaults safe."""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from fvmatch.data.polymarket.constants import (
    CLOB_HOST,
    DATA_API_HOST,
    GAMMA_HOST,
    POLYGON_CHAIN_ID,
    SignatureType,
)


class Settings(BaseSettings):
    """Application settings loaded from environment / .env.

    DRY_RUN defaults to True — the single most important safety.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    supabase_url: str = Field(default="", description="Supabase project URL")
    supabase_service_key: str = Field(
        default="", description="Supabase service role key"
    )
    football_data_api_key: str = Field(
        default="", description="API key for historical data provider"
    )
    dry_run: bool = Field(default=True, description="If True, never place real orders")
    clv_validation_passed: bool = Field(
        default=False,
        description=(
            "Must be True before live execution. Set only after historical "
            "positive-CLV backtest gate passes."
        ),
    )
    model_version: str = Field(
        default="v0", description="Model version tag for model_probs"
    )
    edge_threshold: float = Field(
        default=0.03, description="Min edge (p - price) to consider bet"
    )
    kelly_fraction: float = Field(
        default=0.25, description="Fractional Kelly multiplier"
    )
    kelly_cap: float = Field(
        default=0.05, description="Max bankroll fraction per match (total exposure)"
    )

    # --- Polymarket CLOB V2 (global crypto-native stack) ---
    polymarket_clob_host: str = Field(default=CLOB_HOST, description="CLOB V2 API host")
    polymarket_gamma_host: str = Field(
        default=GAMMA_HOST, description="Gamma discovery API host"
    )
    polymarket_data_host: str = Field(
        default=DATA_API_HOST, description="Data API host (positions, trades)"
    )
    polymarket_chain_id: int = Field(
        default=POLYGON_CHAIN_ID, description="Polygon chain ID (137)"
    )
    polymarket_private_key: str = Field(
        default="", description="EOA private key for L1/L2 CLOB auth (hex, no 0x ok)"
    )
    polymarket_api_key: str = Field(
        default="", description="Optional pre-derived CLOB API key (L2)"
    )
    polymarket_api_secret: str = Field(
        default="", description="Optional pre-derived CLOB API secret (L2)"
    )
    polymarket_api_passphrase: str = Field(
        default="", description="Optional pre-derived CLOB API passphrase (L2)"
    )
    polymarket_signature_type: int = Field(
        default=int(SignatureType.GNOSIS_SAFE),
        description=(
            "CLOB V2 signature type: 0=EOA, 1=POLY_PROXY, 2=GNOSIS_SAFE, "
            "3=POLY_1271 deposit wallet"
        ),
    )
    polymarket_funder: str = Field(
        default="",
        description="Proxy/Safe/deposit wallet address holding pUSD (if not EOA)",
    )
    polymarket_bankroll_pusd: float = Field(
        default=0.0,
        description="Bankroll in pUSD for stake sizing (Kelly fractions → pUSD cost)",
    )
    polymarket_order_type: str = Field(
        default="GTC",
        description="Default order type: GTC, GTD, FOK, or FAK",
    )
    polymarket_price_slippage_bps: int = Field(
        default=50,
        description="Limit price slippage above market for BUY orders (basis points)",
    )

    @field_validator("polymarket_private_key")
    @classmethod
    def strip_private_key_prefix(cls, v: str) -> str:
        v = v.strip()
        if v.startswith("0x") or v.startswith("0X"):
            return v[2:]
        return v

    def polymarket_execution_ready(self) -> bool:
        """True when config has minimum credentials for live CLOB trading."""
        return bool(self.polymarket_private_key) and self.polymarket_bankroll_pusd > 0


settings = Settings()
