"""Gamma + CLOB market snapshots, closing-price capture."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fvmatch.data.polymarket.clob_read import ClobReadClient
from fvmatch.data.polymarket.gamma import GammaClient, GammaMarket
from fvmatch.data.store import MarketSnapshotRow, Store


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _gamma_prices_to_snapshots(
    market: GammaMarket,
    *,
    market_id: int | str,
    is_close: bool = False,
) -> list[MarketSnapshotRow]:
    ts = _now_iso()
    rows: list[MarketSnapshotRow] = []
    for outcome, price in zip(market.outcomes, market.outcome_prices, strict=True):
        row: MarketSnapshotRow = {
            "market_id": market_id,  # type: ignore[typeddict-item]
            "ts": ts,
            "outcome": outcome.lower(),
            "price": price,
            "source": "gamma",
            "is_close": is_close,
        }
        rows.append(row)
    return rows


def _clob_prices_to_snapshots(
    market: GammaMarket,
    *,
    market_id: int | str,
    clob: ClobReadClient,
    is_close: bool = False,
) -> list[MarketSnapshotRow]:
    ts = _now_iso()
    rows: list[MarketSnapshotRow] = []
    for outcome, token_id in zip(market.outcomes, market.clob_token_ids, strict=True):
        try:
            price = clob.get_midpoint(token_id)
        except Exception:
            price = market.price_for_outcome(outcome) or 0.0
        row: MarketSnapshotRow = {
            "market_id": market_id,  # type: ignore[typeddict-item]
            "ts": ts,
            "outcome": outcome.lower(),
            "price": price,
            "source": "clob",
            "is_close": is_close,
        }
        rows.append(row)
    return rows


def snapshot_markets(
    store: Store,
    fixture_ids: list[int | str],
    source: Literal["gamma", "clob"] = "gamma",
    *,
    gamma: GammaClient | None = None,
    clob: ClobReadClient | None = None,
    markets_by_fixture: dict[int | str, GammaMarket] | None = None,
) -> int:
    """Fetch latest prices for match_odds markets and store snapshots.

    For production use, callers resolve fixture_id → GammaMarket (via slug/tag
    search) and pass `markets_by_fixture`. Store persistence remains a stub until
    Supabase upserts are implemented.
    """
    if not markets_by_fixture:
        raise NotImplementedError(
            "markets_by_fixture mapping required — wire fixture→GammaMarket discovery "
            "before store persistence is enabled"
        )

    own_gamma = gamma is None
    own_clob = clob is None
    gamma_client = gamma or GammaClient()
    clob_client = clob or ClobReadClient()

    total = 0
    try:
        for fixture_id in fixture_ids:
            market = markets_by_fixture.get(fixture_id)
            if market is None:
                continue
            if source == "gamma":
                rows = _gamma_prices_to_snapshots(market, market_id=fixture_id)
            else:
                rows = _clob_prices_to_snapshots(
                    market, market_id=fixture_id, clob=clob_client
                )
            store.insert_market_snapshots(rows)
            total += len(rows)
    finally:
        if own_gamma:
            gamma_client.close()
        if own_clob:
            clob_client.close()

    return total


def capture_closing_lines(store: Store, fixture_id: int | str) -> int:
    """After kickoff, mark latest snapshot per outcome as is_close=True."""
    raise NotImplementedError("market.capture_closing_lines awaits store queries")


def get_closing_price(store: Store, market_id: int | str, outcome: str) -> float | None:
    """Return the captured closing price for CLV accounting."""
    raise NotImplementedError("market.get_closing_price awaits store queries")
