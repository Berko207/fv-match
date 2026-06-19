"""Pydantic-settings driven configuration. All secrets via env; defaults safe."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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


settings = Settings()
