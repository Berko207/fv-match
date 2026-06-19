"""CLOB V2 read-only market data (public endpoints, no auth)."""

from __future__ import annotations

from typing import Any

import httpx

from fvmatch.data.polymarket.constants import CLOB_HOST, DATA_API_HOST


class ClobReadClient:
    """Public CLOB + Data API reads for prices, books, and positions."""

    def __init__(
        self,
        clob_host: str = CLOB_HOST,
        data_host: str = DATA_API_HOST,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.clob_host = clob_host.rstrip("/")
        self.data_host = data_host.rstrip("/")
        self._client = client or httpx.Client(timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> ClobReadClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def get_midpoint(self, token_id: str) -> float:
        resp = self._client.get(
            f"{self.clob_host}/midpoint",
            params={"token_id": token_id},
        )
        resp.raise_for_status()
        data = resp.json()
        return float(data["mid"])

    def get_price(self, token_id: str, side: str = "buy") -> float:
        resp = self._client.get(
            f"{self.clob_host}/price",
            params={"token_id": token_id, "side": side},
        )
        resp.raise_for_status()
        data = resp.json()
        return float(data["price"])

    def get_book(self, token_id: str) -> dict[str, Any]:
        resp = self._client.get(
            f"{self.clob_host}/book",
            params={"token_id": token_id},
        )
        resp.raise_for_status()
        payload = resp.json()
        if not isinstance(payload, dict):
            msg = f"Unexpected /book response type: {type(payload)}"
            raise TypeError(msg)
        return payload

    def get_spread(self, token_id: str) -> dict[str, float]:
        resp = self._client.get(
            f"{self.clob_host}/spread",
            params={"token_id": token_id},
        )
        resp.raise_for_status()
        data = resp.json()
        return {"spread": float(data["spread"])}

    def get_positions(
        self,
        user: str,
        *,
        redeemable: bool | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        params: dict[str, str | int | bool] = {
            "user": user,
            "limit": limit,
        }
        if redeemable is not None:
            params["redeemable"] = redeemable
        resp = self._client.get(f"{self.data_host}/positions", params=params)
        resp.raise_for_status()
        payload = resp.json()
        if not isinstance(payload, list):
            msg = f"Unexpected /positions response type: {type(payload)}"
            raise TypeError(msg)
        return payload
