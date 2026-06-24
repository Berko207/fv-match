"""Persist one in-play cycle to Supabase (best-effort time-series capture).

Given a :class:`~fvmatch.engine.MatchAnalysis` produced during a live match, this
records the data needed to compute closing-line value later:

* the parent rows (competition → teams → fixture → match-odds market), created
  idempotently via get-or-create so re-running a live session does not duplicate
  them;
* a ``market_snapshots`` row per priced outcome (the price time-series);
* a ``model_probs`` row (H/D/A) for the current minute/score;
* one ``bets`` row per proposed (dry-run) outcome, entry price fixed at the first
  poll it cleared the gate.

Persistence is always gated by the caller on ``settings.has_supabase`` and run
best-effort — a Supabase failure must never break the live loop.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fvmatch.config import settings
from fvmatch.data.store import Store

if TYPE_CHECKING:
    from fvmatch.engine import MatchAnalysis

# ESPN status state -> fixtures.status vocabulary.
_STATUS_MAP = {"pre": "scheduled", "in": "live", "post": "finished"}


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def persist_live_cycle(
    store: Store,
    analysis: MatchAnalysis,
    *,
    slug: str,
    competition_name: str = "FIFA World Cup 2026",
    season: str = "2026",
    espn_event_id: str | None = None,
    status_state: str = "in",
    kickoff_utc: str | None = None,
    source: str = "gamma",
    is_close: bool = False,
    ts: str | None = None,
) -> dict[str, int]:
    """Persist one in-play snapshot; return counts of rows written.

    Args:
        store: A live :class:`Store` (caller ensures Supabase is configured).
        analysis: The in-play analysis for this cycle (carries ``live_state``).
        slug: Polymarket event slug — the fixture/market external id.
        competition_name, season: Parent competition + season.
        espn_event_id: ESPN event id, stored in ``fixtures.external_ids``.
        status_state: ESPN status state ("pre" | "in" | "post").
        kickoff_utc: Real kickoff if known; defaults to ``ts`` on first create.
        source: Snapshot price source ("gamma" | "clob").
        is_close: Mark these snapshots as the closing line (set on the final poll).
        ts: Snapshot timestamp ISO string; defaults to now.
    """
    ts = ts or _now_iso()
    status = _STATUS_MAP.get(status_state, "scheduled")
    live = analysis.live_state

    comp = store.get_or_create(
        "competitions", {"name": competition_name}, {"kind": "international"}
    )
    comp_id = comp["id"]
    home_team = store.get_or_create(
        "teams", {"competition_id": comp_id, "name": analysis.home}, {}
    )
    away_team = store.get_or_create(
        "teams", {"competition_id": comp_id, "name": analysis.away}, {}
    )

    external_ids: dict[str, str] = {"slug": slug}
    if espn_event_id:
        external_ids["espn_event_id"] = espn_event_id

    fixture = store.get_or_create(
        "fixtures",
        {
            "competition_id": comp_id,
            "home_team_id": home_team["id"],
            "away_team_id": away_team["id"],
            "season": season,
        },
        {
            "kickoff_utc": kickoff_utc or ts,
            "status": status,
            "external_ids": external_ids,
        },
    )
    fixture_id = fixture["id"]

    # Keep the fixture's live score/status current.
    fixture_update: dict[str, object] = {"status": status, "updated_at": ts}
    if live is not None:
        fixture_update["home_goals"] = live.home_goals
        fixture_update["away_goals"] = live.away_goals
    store.update("fixtures", fixture_id, fixture_update)

    market = store.get_or_create(
        "markets",
        {
            "fixture_id": fixture_id,
            "platform": "polymarket",
            "market_type": "match_odds",
        },
        {"external_id": slug},
    )
    market_id = market["id"]

    # market_snapshots: one row per priced outcome (the price time-series).
    snap_rows = [
        {
            "market_id": market_id,
            "ts": ts,
            "outcome": o.outcome,
            "price": o.market_price,
            "source": source,
            "is_close": is_close,
        }
        for o in analysis.outcomes
        if o.market_price is not None
    ]
    if snap_rows:
        store.insert_market_snapshots(snap_rows)  # type: ignore[arg-type]

    # model_probs: H/D/A for this minute/score (matrix omitted to stay light).
    store.insert_model_probs(
        [
            {
                "fixture_id": fixture_id,
                "model_version": settings.model_version,
                "p_home": analysis.p_home,
                "p_draw": analysis.p_draw,
                "p_away": analysis.p_away,
                "scoreline_matrix": None,
            }
        ]
    )

    # bets: one idempotent row per proposed outcome (entry price fixed at first).
    n_bets = 0
    for o in analysis.outcomes:
        if not o.bet or o.market_price is None:
            continue
        store.get_or_create(
            "bets",
            {
                "fixture_id": fixture_id,
                "market_id": market_id,
                "outcome": o.outcome,
            },
            {
                "stake": o.stake_usd,
                "entry_price": o.market_price,
                "model_p": o.model_p,
                "edge": o.edge,
                "kelly_fraction": o.stake_fraction,
                "status": "proposed",
                "dry_run": analysis.dry_run,
            },
        )
        n_bets += 1

    return {"snapshots": len(snap_rows), "model_probs": 1, "bets": n_bets}
