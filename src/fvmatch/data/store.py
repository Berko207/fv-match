"""Supabase client wrapper + typed upsert helpers.

Low-level primitives (``select_one``/``insert``/``update``/``get_or_create``) and
the live time-series inserts (``insert_market_snapshots``/``insert_model_probs``/
``insert_bets``) are implemented against supabase-py using a service-role key on
the tables in 0001_init.sql. The bulk backfill upserts and post-match resolution
helpers remain stubs.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict
from uuid import UUID

# Lazy import to avoid hard dep at import time in Phase 0 scaffold
try:
    from supabase import Client, create_client
except ImportError:  # pragma: no cover
    Client = Any
    create_client = None


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
    """Thin typed wrapper around the Supabase client.

    Primitives + live-persistence inserts are implemented; bulk backfill upserts
    and resolution helpers (``upsert_*``, ``update_bet_resolution``, ``insert_clv``,
    the ``get_*`` queries) are still stubs.
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

    # --- Low-level primitives (PostgREST via supabase-py) ---

    def select_one(self, table: str, match: dict[str, Any]) -> dict[str, Any] | None:
        """Return the first row of ``table`` matching every ``match`` filter."""
        query = self.client.table(table).select("*")
        for column, value in match.items():
            query = query.eq(column, value)
        rows = query.limit(1).execute().data or []
        return rows[0] if rows else None

    def insert(
        self, table: str, rows: list[dict[str, Any]] | dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Insert one or more rows; return the inserted rows (with ids)."""
        payload = rows if isinstance(rows, list) else [rows]
        if not payload:
            return []
        return self.client.table(table).insert(payload).execute().data or []

    def update(
        self, table: str, row_id: UUID | int | str, values: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Update the row with primary key ``row_id``; return it (or None)."""
        rows = (
            self.client.table(table).update(values).eq("id", row_id).execute().data
            or []
        )
        return rows[0] if rows else None

    def get_or_create(
        self,
        table: str,
        match: dict[str, Any],
        defaults: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return the row matching ``match``, else insert ``{**match, **defaults}``.

        Idempotency relies on a single writer (the live loop). For concurrent
        writers add a unique constraint and switch to ``upsert(on_conflict=...)``.
        """
        existing = self.select_one(table, match)
        if existing is not None:
            return existing
        created = self.insert(table, {**match, **(defaults or {})})
        if not created:
            raise RuntimeError(f"insert into {table!r} returned no row")
        return created[0]

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

    def upsert_team_ratings(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Store Elo / other ratings with as_of timestamp."""
        raise NotImplementedError("Phase 0 stub")

    def upsert_markets(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Markets (match_odds, correct_score, etc) + clob_token_ids."""
        raise NotImplementedError("Phase 0 stub")

    def insert_market_snapshots(
        self, rows: list[MarketSnapshotRow]
    ) -> list[dict[str, Any]]:
        """Time-series snapshots. is_close=True for closing line capture."""
        return self.insert("market_snapshots", [dict(r) for r in rows])

    def insert_model_probs(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Store model H/D/A + optional full scoreline_matrix (jsonb)."""
        return self.insert("model_probs", list(rows))

    def insert_bets(self, rows: list[BetRow]) -> list[dict[str, Any]]:
        """Log proposed or executed bets (dry_run flag critical)."""
        return self.insert("bets", [dict(r) for r in rows])

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

    def get_live_markets(self, hours_ahead: int = 48) -> list[dict[str, Any]]:
        """Upcoming fixtures + latest (non-close) market snapshots."""
        raise NotImplementedError("Phase 0 stub")
