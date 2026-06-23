"""Outcome resolution → realized P&L.

Bets are modelled as buying ``stake / entry_price`` shares that each pay $1 if
the outcome occurs and $0 otherwise (Polymarket binary-share convention).
Realized P&L is therefore ``shares - stake`` on a win and ``-stake`` on a loss.
"""

from __future__ import annotations

from typing import Any


def _winning_outcome(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "home"
    if home_goals < away_goals:
        return "away"
    return "draw"


def resolve_bet(
    bet_row: dict[str, Any],
    fixture_result: dict[str, Any],
) -> float:
    """Compute realized P&L (USD) for one bet given the final score.

    Args:
        bet_row: Needs ``outcome``, ``stake``, ``entry_price`` (0<price<=1).
        fixture_result: Needs integer ``home_goals`` and ``away_goals``.

    Returns:
        Realized profit/loss in the same units as ``stake``.
    """
    stake = float(bet_row["stake"])
    entry_price = float(bet_row["entry_price"])
    outcome = str(bet_row["outcome"])
    if stake <= 0:
        return 0.0
    if entry_price <= 0:
        raise ValueError("entry_price must be > 0")

    winner = _winning_outcome(
        int(fixture_result["home_goals"]), int(fixture_result["away_goals"])
    )
    shares = stake / entry_price
    if outcome == winner:
        return shares - stake
    return -stake


def batch_resolve(store_bets: list[dict[str, Any]]) -> int:
    """Resolve a list of bets in place, writing ``realized_pnl``/``status``.

    Each item must include the bet fields plus a nested ``fixture_result`` with
    final goals. Returns the number of bets resolved.
    """
    resolved = 0
    for bet in store_bets:
        result = bet.get("fixture_result")
        if not result:
            continue
        if result.get("home_goals") is None or result.get("away_goals") is None:
            continue
        bet["realized_pnl"] = resolve_bet(bet, result)
        bet["status"] = "resolved"
        resolved += 1
    return resolved
