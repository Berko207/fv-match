"""De-vigging methods for converting raw bookmaker/market prices (decimal odds)
into estimated true outcome probabilities that sum to 1.0.

All functions are pure, deterministic, and I/O-free. Prices are assumed to be
decimal odds > 1.0 (e.g. 2.5 means +150 US). No validation for now (later in gate).
"""

from __future__ import annotations

from typing import Literal


def multiplicative(prices: list[float]) -> list[float]:
    """Multiplicative (proportional) de-vig.

    Converts implied probabilities r_i = 1/price_i by normalizing their sum to 1.
    This spreads the overround proportionally to each outcome's raw weight.

    Args:
        prices: List of decimal odds (>1.0). Length >= 2.

    Returns:
        List of de-vigged probabilities summing to ~1.0 (within 1e-12 fp error).
    """
    if not prices:
        return []
    implied = [1.0 / p for p in prices]
    total = sum(implied)
    if total == 0:
        return [0.0] * len(prices)
    return [imp / total for imp in implied]


def power(prices: list[float], tol: float = 1e-10, max_iter: int = 100) -> list[float]:
    """Power (exponential) de-vig via binary search for exponent k.

    Solves for k such that sum(r_i ** k) == 1 where r_i = 1/price_i, then
    p_i = r_i ** k. For typical overround (sum r > 1), k > 1 which widens
    the probability gap between favorites and longshots relative to multiplicative.

    Pure Python binary search (no scipy) for determinism and minimal deps.

    Args:
        prices: List of decimal odds.
        tol: Convergence tolerance on |sum(p) - 1|.
        max_iter: Safety cap on bisection iterations.

    Returns:
        De-vigged probs summing to 1.0 within tol.
    """
    if not prices:
        return []
    r = [1.0 / p for p in prices]
    s = sum(r)
    if abs(s - 1.0) < 1e-12:
        return r[:]

    # Bracket k: for overround s>1 we expect k>1; underround k<1 possible
    lo, hi = 0.1, 10.0
    for _ in range(max_iter):
        mid = (lo + hi) / 2.0
        val = sum(ri ** mid for ri in r)
        if abs(val - 1.0) < tol:
            break
        if val > 1.0:
            lo = mid  # need higher k to reduce sum(r**k)
        else:
            hi = mid
    k = (lo + hi) / 2.0
    probs = [ri ** k for ri in r]
    total = sum(probs)
    if total == 0:
        return [0.0] * len(prices)
    return [p / total for p in probs]  # fp safety


def shin(prices: list[float]) -> list[float]:
    """Shin's insider-trading de-vig model (closed-form multi-outcome variant).

    Estimates insider proportion z = (sum(r) - 1) / (n - 1), then
    p_i = (r_i - z) / (1 - z) where r_i = 1/price_i.
    This is the standard linear adjustment used for Shin in n-way markets
    (reduces to additive for n=2). It widens the favorite-longshot gap
    vs multiplicative (more prob mass on favorites, less on longshots).

    See Shin (1992, 1993) and common betting implementations.

    Args:
        prices: List of decimal odds.

    Returns:
        De-vigged probabilities summing exactly to 1.0 (within fp).
    """
    if not prices:
        return []
    n = len(prices)
    if n < 2:
        return [1.0]
    r = [1.0 / p for p in prices]
    s = sum(r)
    if n == 1:
        return [1.0]
    z = (s - 1.0) / (n - 1.0)
    # Guard z in [0, min(r)) to keep p>0
    z = max(0.0, min(z, min(r) - 1e-12))
    denom = 1.0 - z
    if denom <= 0:
        # Fallback to multiplicative if degenerate
        return multiplicative(prices)
    probs = [(ri - z) / denom for ri in r]
    # Renormalize for any fp drift or z clipping
    total = sum(probs)
    if total <= 0:
        return multiplicative(prices)
    return [max(0.0, p / total) for p in probs]


Method = Literal["multiplicative", "power", "shin"]


def devig(prices: list[float], method: Method = "shin") -> list[float]:
    """Dispatcher for de-vig methods. Default: 'shin' (recommended for accuracy).

    Args:
        prices: Decimal odds for the outcomes (H, D, A or other).
        method: One of 'multiplicative', 'power', 'shin'.

    Returns:
        True probabilities (sum ≈ 1.0).
    """
    if method == "multiplicative":
        return multiplicative(prices)
    if method == "power":
        return power(prices)
    if method == "shin":
        return shin(prices)
    raise ValueError(f"Unknown de-vig method: {method}")
