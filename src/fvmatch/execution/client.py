"""Adapter to Polymarket CLOB V2 via py-clob-client-v2.

Never places real orders when DRY_RUN=true (the default). Live execution
requires DRY_RUN=false, CLV_VALIDATION_PASSED=true, and configured wallet creds.
"""

from __future__ import annotations

import logging
from typing import Any

from fvmatch.config import settings
from fvmatch.edge.kelly import Leg
from fvmatch.execution.clob import (
    PolymarketClobExecutor,
    apply_buy_slippage,
    stake_fraction_to_shares,
)

logger = logging.getLogger(__name__)


def _assert_live_execution_allowed() -> None:
    if settings.dry_run:
        raise RuntimeError("DRY_RUN=true — refusing live CLOB execution")
    if not settings.clv_validation_passed:
        raise RuntimeError(
            "CLV_VALIDATION_PASSED=false — historical positive-CLV gate not cleared"
        )
    if not settings.polymarket_execution_ready():
        raise RuntimeError(
            "Polymarket credentials incomplete — set POLYMARKET_PRIVATE_KEY and "
            "POLYMARKET_BANKROLL_PUSD"
        )


def place_bets(
    legs: list[Leg],
    stakes: list[float],
    fixture_id: int | str,
    *,
    token_ids: dict[str, str] | None = None,
    tick_sizes: dict[str, str] | None = None,
    neg_risk: bool = False,
    dry_run: bool | None = None,
    bankroll_pusd: float | None = None,
) -> list[dict[str, Any]]:
    """Submit stakes to Polymarket CLOB V2 for the given legs on one match.

    Args:
        legs: Kelly legs with outcome labels and model/market prices.
        stakes: Bankroll fractions from joint_match_stakes (same order as legs).
        fixture_id: Fixture identifier for logging/accounting.
        token_ids: Map outcome label → CLOB token ID (required for live path).
        tick_sizes: Optional per-outcome tick size strings from Gamma/CLOB info.
        neg_risk: True for negative-risk (multi-outcome) markets.
        dry_run: Override settings.dry_run when set.
        bankroll_pusd: Override settings.polymarket_bankroll_pusd when set.

    Returns:
        List of fill dicts with leg, stake, status, order_id, tx_hash (None on CLOB).
    """
    effective_dry = dry_run if dry_run is not None else settings.dry_run
    bankroll = (
        bankroll_pusd
        if bankroll_pusd is not None
        else settings.polymarket_bankroll_pusd
    )

    if effective_dry:
        return [
            {
                "fixture_id": fixture_id,
                "leg": leg.outcome,
                "stake": stake,
                "price": leg.price,
                "status": "simulated",
                "order_id": None,
                "tx_hash": None,
            }
            for leg, stake in zip(legs, stakes, strict=True)
        ]

    _assert_live_execution_allowed()
    if not token_ids:
        raise ValueError("token_ids mapping is required for live CLOB execution")

    executor = PolymarketClobExecutor()
    results: list[dict[str, Any]] = []

    for leg, stake in zip(legs, stakes, strict=True):
        if stake <= 0:
            continue

        token_id = token_ids.get(leg.outcome)
        if not token_id:
            logger.warning(
                "Skipping leg %s on fixture %s — no token_id",
                leg.outcome,
                fixture_id,
            )
            continue

        limit_price = apply_buy_slippage(
            leg.price, settings.polymarket_price_slippage_bps
        )
        shares, cost = stake_fraction_to_shares(stake, bankroll, limit_price)
        if shares <= 0:
            continue

        tick = (tick_sizes or {}).get(leg.outcome)
        order = executor.buy_limit(
            token_id=token_id,
            outcome=leg.outcome,
            price=limit_price,
            size=shares,
            tick_size=tick,
            neg_risk=neg_risk,
        )
        results.append(
            {
                "fixture_id": fixture_id,
                "leg": leg.outcome,
                "stake": stake,
                "price": limit_price,
                "size": order.size,
                "cost_pusd": order.cost_pusd,
                "status": order.status,
                "order_id": order.order_id,
                "tx_hash": None,
                "token_id": token_id,
            }
        )
        logger.info(
            "CLOB order fixture=%s outcome=%s order_id=%s status=%s cost=%.4f pUSD",
            fixture_id,
            leg.outcome,
            order.order_id,
            order.status,
            order.cost_pusd,
        )

    return results


def cancel_all_pending(fixture_id: int | str | None = None) -> int:
    """Cancel open CLOB orders. fixture_id reserved for per-market cancel later."""
    if settings.dry_run:
        logger.info(
            "[DRY_RUN] Would cancel pending CLOB orders (fixture=%s)", fixture_id
        )
        return 0

    _assert_live_execution_allowed()
    executor = PolymarketClobExecutor()
    canceled = executor.cancel_all()
    logger.info("Canceled %s CLOB orders (fixture=%s)", canceled, fixture_id)
    return canceled
