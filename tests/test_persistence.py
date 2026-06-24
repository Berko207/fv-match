"""Tests for live-cycle Supabase persistence using an in-memory fake store.

No network or supabase package required — ``FakeStore`` duck-types the handful of
``Store`` methods :func:`persist_live_cycle` calls and records what was written.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from fvmatch.data.persistence import persist_live_cycle
from fvmatch.engine import analyze_live_match
from fvmatch.model.live import LiveState


class FakeStore:
    """Records get_or_create / update / insert calls in memory."""

    def __init__(self) -> None:
        self.rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.snapshots: list[dict[str, Any]] = []
        self.model_probs: list[dict[str, Any]] = []
        self.updates: list[tuple[str, Any, dict[str, Any]]] = []
        self._next_id = 0

    def _new_id(self) -> str:
        self._next_id += 1
        return f"id-{self._next_id}"

    def get_or_create(
        self,
        table: str,
        match: dict[str, Any],
        defaults: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        for row in self.rows[table]:
            if all(row.get(k) == v for k, v in match.items()):
                return row
        row = {"id": self._new_id(), **match, **(defaults or {})}
        self.rows[table].append(row)
        return row

    def update(
        self, table: str, row_id: Any, values: dict[str, Any]
    ) -> dict[str, Any] | None:
        self.updates.append((table, row_id, values))
        for row in self.rows[table]:
            if row.get("id") == row_id:
                row.update(values)
                return row
        return None

    def insert_market_snapshots(
        self, rows: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        self.snapshots.extend(rows)
        return list(rows)

    def insert_model_probs(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self.model_probs.extend(rows)
        return list(rows)


def _analysis():
    """In-play analysis where the draw is underpriced -> a proposed bet."""
    state = LiveState(minute=71, home_goals=0, away_goals=0)
    return analyze_live_match(
        home="Colombia",
        away="DR Congo",
        state=state,
        home_odds=2.11,
        draw_odds=2.20,
        away_odds=15.38,
    )


def test_persist_live_cycle_writes_expected_rows() -> None:
    store = FakeStore()
    analysis = _analysis()

    counts = persist_live_cycle(
        store,  # type: ignore[arg-type]
        analysis,
        slug="fifwc-col-cdr-2026-06-23",
        espn_event_id="760459",
        status_state="in",
        ts="2026-06-23T20:00:00Z",
    )

    # Parents created once each.
    assert len(store.rows["competitions"]) == 1
    assert len(store.rows["teams"]) == 2
    assert len(store.rows["fixtures"]) == 1
    assert len(store.rows["markets"]) == 1

    fixture = store.rows["fixtures"][0]
    assert fixture["external_ids"]["slug"] == "fifwc-col-cdr-2026-06-23"
    assert fixture["external_ids"]["espn_event_id"] == "760459"
    assert fixture["status"] == "live"

    # One snapshot per priced outcome.
    assert len(store.snapshots) == 3
    assert {s["outcome"] for s in store.snapshots} == {"home", "draw", "away"}
    assert all(s["source"] == "gamma" for s in store.snapshots)
    assert all(s["is_close"] is False for s in store.snapshots)
    assert all(0.0 < s["price"] < 1.0 for s in store.snapshots)
    assert all(s["ts"] == "2026-06-23T20:00:00Z" for s in store.snapshots)

    # One model-probs row that sums to 1.
    assert len(store.model_probs) == 1
    mp = store.model_probs[0]
    assert abs(mp["p_home"] + mp["p_draw"] + mp["p_away"] - 1.0) < 1e-6

    # Proposed bets are dry-run with the entry price = market price.
    bets = store.rows["bets"]
    assert len(bets) >= 1
    for bet in bets:
        assert bet["dry_run"] is True
        assert bet["status"] == "proposed"
        assert 0.0 < bet["entry_price"] < 1.0

    assert counts["snapshots"] == 3
    assert counts["model_probs"] == 1
    assert counts["bets"] == len(bets)


def test_persist_is_idempotent_on_parents_and_bets() -> None:
    store = FakeStore()
    analysis = _analysis()

    persist_live_cycle(store, analysis, slug="s", status_state="in", ts="t1")  # type: ignore[arg-type]
    persist_live_cycle(store, analysis, slug="s", status_state="in", ts="t2")  # type: ignore[arg-type]

    # Parents + bets are not duplicated across cycles.
    assert len(store.rows["competitions"]) == 1
    assert len(store.rows["teams"]) == 2
    assert len(store.rows["fixtures"]) == 1
    assert len(store.rows["markets"]) == 1
    n_proposed = sum(1 for o in analysis.outcomes if o.bet)
    assert len(store.rows["bets"]) == n_proposed

    # Snapshots + model probs are append-only time series.
    assert len(store.snapshots) == 6
    assert len(store.model_probs) == 2


def test_is_close_and_finished_status_propagate() -> None:
    store = FakeStore()
    analysis = _analysis()

    persist_live_cycle(
        store,  # type: ignore[arg-type]
        analysis,
        slug="s",
        status_state="post",
        is_close=True,
        ts="t",
    )

    assert all(s["is_close"] is True for s in store.snapshots)
    assert store.rows["fixtures"][0]["status"] == "finished"


def test_fixture_score_updated_from_live_state() -> None:
    store = FakeStore()
    state = LiveState(minute=80, home_goals=2, away_goals=1)
    analysis = analyze_live_match(home="Colombia", away="DR Congo", state=state)

    persist_live_cycle(store, analysis, slug="s", status_state="in")  # type: ignore[arg-type]

    fixture = store.rows["fixtures"][0]
    assert fixture["home_goals"] == 2
    assert fixture["away_goals"] == 1
    # Model-only (no odds) -> no priced snapshots, no bets.
    assert store.snapshots == []
    assert store.rows["bets"] == []
