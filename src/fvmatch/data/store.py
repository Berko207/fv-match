"""Supabase client wrapper + typed upsert helpers.

Phase 0: fully stubbed. Real implementation will use service-role key for
insert/upsert on the tables defined in 0001_init.sql.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict
from uuid import UUID

# Lazy import to avoid hard dep at import time in Phase 0 scaffold
try:
    from supabase import Client, create_client
except ImportError:  # pragma: no cover
    Client = Any  # type: ignore[misc, assignment]
    create_client = None  # type: ignore[assignment]


class FixtureRow(TypedDict, total=False):
    id: UUID | int
    competition_id: UUID | int
    season: str
    home_team_id: UUID | int
    away_team_id: UUID | int
    kickoff_utc: str
    status: str
    home_goals: int | None
    away_goals: int | None
    external_ids: dict[str, Any]


class MarketSnapshotRow(TypedDict, total=False):
    market_id: UUID | int
    ts: str
    outcome: str
    price: float
    source: Literal["gamma", "clob"]
    is_close: bool


class BetRow(TypedDict, total=False):
    id: UUID | int
    market_id: UUID | int
    fixture_id: UUID | int
    outcome: str
    stake: float
    entry_price: float
    model_p: float
    edge: float
    kelly_fraction: float
    status: str
    dry_run: bool
    realized_pnl: float | None


class Store:
    """Thin typed wrapper around Supabase client.

    All methods are STUBS in Phase 0 — they document the intended contract.
    """

    def __init__(self, url: str | None = None, key: str | None = None) -> None:
        self.url = url
        self.key = key
        self._client: Client | None = None

    @property
    def client(self) -> Client:
        if self._client is None:
            if create_client is None:
                raise RuntimeError("supabase package not installed (uv sync)")
            self._client = create_client(self.url or "", self.key or "")
        return self._client

    # --- Stubs with full signatures + docstrings ---

    def upsert_competitions(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Upsert into competitions table. Returns inserted/updated rows."""
        raise NotImplementedError("Phase 0 stub")

    def upsert_teams(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Upsert teams with competition FK."""
        raise NotImplementedError("Phase 0 stub")

    def upsert_fixtures(self, rows: list[FixtureRow]) -> list[dict[str, Any]]:
        """Bulk upsert fixtures. Used by backfill and live polling."""
        raise NotImplementedError("Phase 0 stub")

    def upsert_team_ratings(
        self, rows: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Store Elo / other ratings with as_of timestamp."""
        raise NotImplementedError("Phase 0 stub")

    def upsert_markets(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Markets (match_odds, correct_score, etc) + clob_token_ids."""
        raise NotImplementedError("Phase 0 stub")

    def insert_market_snapshots(
        self, rows: list[MarketSnapshotRow]
    ) -> list[dict[str, Any]]:
        """Time-series snapshots. is_close=True for closing line capture."""
        raise NotImplementedError("Phase 0 stub")

    def insert_model_probs(
        self, rows: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Store model H/D/A + full scoreline_matrix (jsonb)."""
        raise NotImplementedError("Phase 0 stub")

    def insert_bets(self, rows: list[BetRow]) -> list[dict[str, Any]]:
        """Log proposed or executed bets (dry_run flag critical)."""
        raise NotImplementedError("Phase 0 stub")

    def update_bet_resolution(
        self, bet_id: UUID | int, realized_pnl: float, status: str = "resolved"
    ) -> dict[str, Any]:
        """After match result, update realized_pnl and status."""
        raise NotImplementedError("Phase 0 stub")

    def insert_clv(
        self, bet_id: UUID | int, close_price: float, clv_pct: float
    ) -> dict[str, Any]:
        """Record closing line value for a bet (computed post-close)."""
        raise NotImplementedError("Phase 0 stub")

    def get_fixtures_for_model(
        self, competition_id: UUID | int | None = None, season: str | None = None
    ) -> list[dict[str, Any]]:
        """Query fixtures ready for modeling (with teams, ratings joined)."""
        raise NotImplementedError("Phase 0 stub")

    def get_live_markets(
        self, hours_ahead: int = 48
    ) -> list[dict[str, Any]]:
        """Upcoming fixtures + latest (non-close) market snapshots."""
        raise NotImplementedError("Phase 0 stub")
