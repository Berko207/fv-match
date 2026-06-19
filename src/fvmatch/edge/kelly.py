"""Fractional Kelly staking for binary and multi-outcome (mutually exclusive) bets.

All functions are pure, deterministic, I/O-free, and fully type-hinted.
Used after de-vig to size bets only on positive edge.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Leg:
    """One leg of a multi-outcome market on the SAME match.

    outcome: e.g. 'home', 'draw', 'away' (or 'over', etc for other markets)
    p: model's estimated true probability for this outcome
    price: current de-vigged? or raw market price (cost per $1 payout share)
    """

    outcome: str
    p: float
    price: float


def kelly_fraction(p: float, price: float) -> float:
    """Optimal Kelly fraction for a binary bet on a share that pays $1 if wins.

    The bet costs `price` per share (0 < price < 1). If model prob p > price
    (positive edge), the full Kelly stake fraction f* of bankroll is
    (p - price) / (1 - price). This is the fraction of bankroll to allocate
    to purchasing shares (total cost = f * bankroll).

    Clamps to 0.0 on non-positive edge (p <= price or price >=1).

    Args:
        p: Model's estimated probability of the outcome winning (0..1].
        price: Market price of the $1-payout share (0 < price < 1).

    Returns:
        Kelly fraction in [0, 1].
    """
    if p <= price or price >= 1.0 or price <= 0.0:
        return 0.0
    return (p - price) / (1.0 - price)


def fractional_kelly(
    p: float, price: float, fraction: float = 0.25, cap: float = 0.05
) -> float:
    """Fractional Kelly with safety cap.

    Scales full Kelly by `fraction` (e.g. 0.25 = quarter-Kelly) then caps
    at `cap` fraction of bankroll (e.g. 0.05 = 5% max per bet).

    Args:
        p, price: See kelly_fraction.
        fraction: Kelly multiplier (0 < fraction <= 1).
        cap: Hard max bankroll allocation per leg (0 < cap <= 1).

    Returns:
        Stake fraction in [0, cap].
    """
    full = kelly_fraction(p, price)
    scaled = full * max(0.0, min(fraction, 1.0))
    return min(scaled, max(0.0, cap))


def joint_match_stakes(
    legs: list[Leg], fraction: float = 0.25, cap: float = 0.05
) -> list[float]:
    """Compute stakes for multiple correlated legs on the *same* match.

    Since outcomes are mutually exclusive (exactly one resolves win, others lose),
    we cannot win on >1 leg. However, the capital at risk is the *sum* of
    individual stake costs.

    Simplification used (full joint Kelly / correlated optimization is TODO):
    1. Compute fractional_kelly independently for each leg.
    2. If sum(individual_stakes) > cap, scale ALL stakes proportionally
       so that total exposure == cap. This prevents over-committing bankroll
       to one match while still allocating relative to each leg's edge.
    3. Never returns stakes whose sum exceeds `cap`.

    This is conservative and practical; a true multi-outcome Kelly would
    solve a constrained optimization (e.g. Dirichlet or log-utility max
    under p vector and mutually-exclusive constraint) — future work.

    Args:
        legs: List of Leg dataclasses for outcomes on one fixture.
        fraction, cap: See fractional_kelly.

    Returns:
        List of stake fractions (same order as legs), each in [0, cap],
        with sum(returns) <= cap.
    """
    if not legs:
        return []

    raw_stakes: list[float] = []
    for leg in legs:
        s = fractional_kelly(leg.p, leg.price, fraction=fraction, cap=cap)
        raw_stakes.append(s)

    total_raw = sum(raw_stakes)
    if total_raw <= cap + 1e-12:
        return raw_stakes

    # Scale down proportionally to respect cap (preserves relative sizing)
    scale = cap / total_raw if total_raw > 0 else 0.0
    scaled = [s * scale for s in raw_stakes]
    # fp safety: ensure sum <= cap
    return [min(s, cap) for s in scaled]
