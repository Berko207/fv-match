"""STUB: Gamma + CLOB market snapshots, closing-price capture."""

from __future__ import annotations

from typing import Literal

from fvmatch.data.store import Store


def snapshot_markets(
    store: Store,
    fixture_ids: list[int | str],
    source: Literal["gamma", "clob"] = "gamma",
) -> int:
    """Fetch latest prices for match_odds / correct_score markets and store snapshots.

    For CLOB also captures orderbook depth if needed later.
    Phase 0: STUB.
    """
    raise NotImplementedError("market.snapshot_markets is a Phase 0 stub")


def capture_closing_lines(store: Store, fixture_id: int | str) -> int:
    """After kickoff or at settlement, mark latest snapshot per outcome as is_close=True.

    Critical for CLV calculation (entry_price vs close_price).
    Phase 0: STUB.
    """
    raise NotImplementedError("market.capture_closing_lines is a Phase 0 stub")


def get_closing_price(store: Store, market_id: int | str, outcome: str) -> float | None:
    """Return the captured closing price for CLV accounting."""
    raise NotImplementedError("market.get_closing_price is a Phase 0 stub")
