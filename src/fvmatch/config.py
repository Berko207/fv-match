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

    # --- Model (Dixon-Coles + Elo prior) parameters ---
    base_goals: float = Field(
        default=2.6,
        description="Baseline expected total goals for an evenly-matched fixture",
    )
    elo_goal_scale: float = Field(
        default=150.0,
        description="Elo points per 1 goal of expected supremacy (lower = bigger edge)",
    )
    home_advantage_elo: float = Field(
        default=65.0,
        description="Elo points added to the home team (0 for neutral venues)",
    )
    dc_rho: float = Field(
        default=-0.08,
        description="Dixon-Coles low-score correlation parameter (typically negative)",
    )
    dc_decay: float = Field(
        default=0.003, description="Per-day time-decay weight for Dixon-Coles fit"
    )
    max_goals: int = Field(
        default=10, description="Max goals per side in the scoreline matrix"
    )

    # --- Risk / accounting ---
    bankroll: float = Field(
        default=1000.0, description="Bankroll in USD used to convert stake fractions"
    )
    min_liquidity_usd: float = Field(
        default=5000.0,
        description="Minimum market liquidity to clear the liquidity gate",
    )
    devig_method: str = Field(
        default="shin", description="De-vig method: multiplicative | power | shin"
    )

    @property
    def has_supabase(self) -> bool:
        """True when Supabase credentials are configured."""
        return bool(self.supabase_url and self.supabase_service_key)


settings = Settings()
