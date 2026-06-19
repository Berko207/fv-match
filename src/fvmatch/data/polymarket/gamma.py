"""Gamma API client — market discovery, token IDs, outcome prices."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx

from fvmatch.data.polymarket.constants import GAMMA_HOST


@dataclass(frozen=True)
class GammaMarket:
    """Parsed Gamma market row with CLOB token mapping."""

    market_id: str
    condition_id: str
    question: str
    slug: str
    outcomes: tuple[str, ...]
    outcome_prices: tuple[float, ...]
    clob_token_ids: tuple[str, ...]
    neg_risk: bool
    tick_size: str
    min_order_size: float
    active: bool
    closed: bool
    liquidity_usd: float
    volume_usd: float
    raw: dict[str, Any]

    def token_id_for_outcome(self, outcome: str) -> str | None:
        """Map outcome label (case-insensitive) to CLOB token ID."""
        key = outcome.strip().lower()
        for label, token_id in zip(self.outcomes, self.clob_token_ids, strict=True):
            if label.strip().lower() == key:
                return token_id
        return None

    def price_for_outcome(self, outcome: str) -> float | None:
        key = outcome.strip().lower()
        for label, price in zip(self.outcomes, self.outcome_prices, strict=True):
            if label.strip().lower() == key:
                return price
        return None


def _parse_json_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        parsed: list[Any] = json.loads(value)
        return parsed
    return list(value)


def _parse_gamma_market(row: dict[str, Any]) -> GammaMarket:
    outcomes = tuple(str(x) for x in _parse_json_list(row.get("outcomes")))
    prices_raw = _parse_json_list(row.get("outcomePrices"))
    prices = tuple(float(x) for x in prices_raw)
    token_ids = tuple(str(x) for x in _parse_json_list(row.get("clobTokenIds")))

    tick = row.get("orderPriceMinTickSize")
    tick_size = str(tick) if tick is not None else "0.01"

    return GammaMarket(
        market_id=str(row.get("id", "")),
        condition_id=str(row.get("conditionId", "")),
        question=str(row.get("question", "")),
        slug=str(row.get("slug", "")),
        outcomes=outcomes,
        outcome_prices=prices,
        clob_token_ids=token_ids,
        neg_risk=bool(row.get("negRisk", False)),
        tick_size=tick_size,
        min_order_size=float(row.get("orderMinSize") or 0.0),
        active=bool(row.get("active", False)),
        closed=bool(row.get("closed", False)),
        liquidity_usd=float(row.get("liquidityNum") or row.get("liquidity") or 0.0),
        volume_usd=float(row.get("volumeNum") or row.get("volume") or 0.0),
        raw=row,
    )


class GammaClient:
    """Read-only Gamma API client (no auth required)."""

    def __init__(
        self,
        host: str = GAMMA_HOST,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.host = host.rstrip("/")
        self._client = client or httpx.Client(timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> GammaClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def fetch_markets(
        self,
        *,
        tag: str | None = None,
        slug: str | None = None,
        active: bool | None = True,
        closed: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[GammaMarket]:
        """Fetch markets from Gamma. Use tag='soccer' for football match markets."""
        params: dict[str, str | int | bool] = {
            "limit": limit,
            "offset": offset,
        }
        if tag is not None:
            params["tag"] = tag
        if slug is not None:
            params["slug"] = slug
        if active is not None:
            params["active"] = active
        if closed is not None:
            params["closed"] = closed

        resp = self._client.get(f"{self.host}/markets", params=params)
        resp.raise_for_status()
        payload = resp.json()
        if not isinstance(payload, list):
            msg = f"Unexpected Gamma /markets response type: {type(payload)}"
            raise TypeError(msg)
        return [_parse_gamma_market(row) for row in payload]

    def fetch_market_by_slug(self, slug: str) -> GammaMarket | None:
        markets = self.fetch_markets(slug=slug, limit=1)
        return markets[0] if markets else None

    def fetch_market_by_condition_id(self, condition_id: str) -> GammaMarket | None:
        resp = self._client.get(
            f"{self.host}/markets",
            params={"condition_ids": condition_id, "limit": 1},
        )
        resp.raise_for_status()
        payload = resp.json()
        if not isinstance(payload, list) or not payload:
            return None
        return _parse_gamma_market(payload[0])
