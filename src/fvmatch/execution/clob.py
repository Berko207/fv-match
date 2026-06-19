"""Authenticated Polymarket CLOB V2 client wrapper (py-clob-client-v2)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from py_clob_client_v2 import (
    ApiCreds,
    ClobClient,
    MarketOrderArgs,
    OrderArgs,
    OrderType,
    PartialCreateOrderOptions,
    Side,
)

from fvmatch.config import Settings, settings
from fvmatch.data.polymarket.constants import SignatureType

logger = logging.getLogger(__name__)

ORDER_TYPE_MAP: dict[str, OrderType] = {
    "GTC": OrderType.GTC,
    "GTD": OrderType.GTD,
    "FOK": OrderType.FOK,
    "FAK": OrderType.FAK,
}


@dataclass(frozen=True)
class OrderResult:
    """Normalized result from a CLOB order submission."""

    outcome: str
    token_id: str
    side: str
    price: float
    size: float
    cost_pusd: float
    order_id: str | None
    status: str
    raw: dict[str, Any]


class PolymarketClobExecutor:
    """Thin wrapper around py-clob-client-v2 for fv-match execution."""

    def __init__(self, cfg: Settings | None = None) -> None:
        self.cfg = cfg or settings
        self._client: ClobClient | None = None

    def _validate_live_config(self) -> None:
        if not self.cfg.polymarket_private_key:
            raise RuntimeError(
                "POLYMARKET_PRIVATE_KEY is required for live CLOB execution"
            )
        if self.cfg.polymarket_bankroll_pusd <= 0:
            raise RuntimeError(
                "POLYMARKET_BANKROLL_PUSD must be > 0 for live stake sizing"
            )
        if int(self.cfg.polymarket_signature_type) == int(SignatureType.POLY_1271):
            logger.warning(
                "signature_type=3 (POLY_1271 deposit wallet) has known Python SDK "
                "issues as of mid-2026 — validate on small orders or use type 2"
            )

    def _build_creds(self) -> ApiCreds | None:
        key = self.cfg.polymarket_api_key
        secret = self.cfg.polymarket_api_secret
        passphrase = self.cfg.polymarket_api_passphrase
        if key and secret and passphrase:
            return ApiCreds(api_key=key, api_secret=secret, api_passphrase=passphrase)
        return None

    def get_client(self, *, authenticate: bool = True) -> ClobClient:
        """Return authenticated ClobClient, deriving API creds if needed."""
        if self._client is not None and authenticate:
            return self._client

        funder = self.cfg.polymarket_funder or None
        signature_type = (
            self.cfg.polymarket_signature_type
            if self.cfg.polymarket_signature_type is not None
            else None
        )
        creds = self._build_creds()

        client = ClobClient(
            host=self.cfg.polymarket_clob_host,
            chain_id=self.cfg.polymarket_chain_id,
            key=self.cfg.polymarket_private_key,
            creds=creds,
            signature_type=signature_type,
            funder=funder,
        )

        if authenticate and creds is None:
            derived = client.create_or_derive_api_key()
            client = ClobClient(
                host=self.cfg.polymarket_clob_host,
                chain_id=self.cfg.polymarket_chain_id,
                key=self.cfg.polymarket_private_key,
                creds=derived,
                signature_type=signature_type,
                funder=funder,
            )

        self._client = client
        return client

    def resolve_order_type(self, order_type: str | None = None) -> OrderType:
        key = (order_type or self.cfg.polymarket_order_type).upper()
        if key not in ORDER_TYPE_MAP:
            msg = f"Unsupported order type: {key}"
            raise ValueError(msg)
        return ORDER_TYPE_MAP[key]

    def buy_limit(
        self,
        *,
        token_id: str,
        outcome: str,
        price: float,
        size: float,
        tick_size: str | None = None,
        neg_risk: bool = False,
        order_type: str | None = None,
    ) -> OrderResult:
        """Place a limit BUY for `size` outcome shares at `price`."""
        self._validate_live_config()
        client = self.get_client()
        ot = self.resolve_order_type(order_type)

        options: PartialCreateOrderOptions | None = None
        if tick_size is not None:
            options = PartialCreateOrderOptions(tick_size=tick_size, neg_risk=neg_risk)

        resp = client.create_and_post_order(
            order_args=OrderArgs(
                token_id=token_id,
                price=price,
                side=Side.BUY,
                size=size,
            ),
            options=options,
            order_type=ot,
        )
        return _normalize_order_response(
            resp,
            outcome=outcome,
            token_id=token_id,
            side="BUY",
            price=price,
            size=size,
        )

    def buy_market_fok(
        self,
        *,
        token_id: str,
        outcome: str,
        amount_pusd: float,
        tick_size: str | None = None,
        neg_risk: bool = False,
    ) -> OrderResult:
        """Market BUY (FOK) spending `amount_pusd` pUSD."""
        self._validate_live_config()
        client = self.get_client()

        options: PartialCreateOrderOptions | None = None
        if tick_size is not None:
            options = PartialCreateOrderOptions(tick_size=tick_size, neg_risk=neg_risk)

        resp = client.create_and_post_market_order(
            order_args=MarketOrderArgs(
                token_id=token_id,
                amount=amount_pusd,
                side=Side.BUY,
                order_type=OrderType.FOK,
            ),
            options=options,
            order_type=OrderType.FOK,
        )
        return _normalize_order_response(
            resp,
            outcome=outcome,
            token_id=token_id,
            side="BUY",
            price=0.0,
            size=0.0,
            cost_pusd=amount_pusd,
        )

    def cancel_all(self, market: str | None = None) -> int:
        """Cancel all open orders, optionally scoped to one condition/market."""
        self._validate_live_config()
        client = self.get_client()
        if market:
            resp = client.cancel_market_orders(market=market)
        else:
            resp = client.cancel_all()
        if isinstance(resp, dict):
            canceled = resp.get("canceled") or resp.get("count") or 0
            return int(canceled)
        return 0

    def get_balance_allowance(self) -> dict[str, Any]:
        """Return pUSD balance/allowance from CLOB (requires auth)."""
        self._validate_live_config()
        client = self.get_client()
        raw = client.get_balance_allowance()
        if isinstance(raw, dict):
            return raw
        return {"raw": raw}


def stake_fraction_to_shares(
    stake_fraction: float,
    bankroll_pusd: float,
    price: float,
) -> tuple[float, float]:
    """Convert Kelly stake fraction to (share_count, cost_pusd).

    Each share costs `price` pUSD and pays $1 if the outcome wins.
    """
    if stake_fraction <= 0 or bankroll_pusd <= 0 or price <= 0 or price >= 1:
        return 0.0, 0.0
    cost = stake_fraction * bankroll_pusd
    shares = cost / price
    return shares, cost


def apply_buy_slippage(price: float, slippage_bps: int) -> float:
    """Raise limit price for BUY orders by slippage (capped below 1)."""
    adjusted = price * (1.0 + slippage_bps / 10_000.0)
    return min(adjusted, 0.9999)


def _normalize_order_response(
    resp: Any,
    *,
    outcome: str,
    token_id: str,
    side: str,
    price: float,
    size: float,
    cost_pusd: float | None = None,
) -> OrderResult:
    if not isinstance(resp, dict):
        resp = {"raw": resp}
    order_id = resp.get("orderID") or resp.get("order_id")
    status = str(resp.get("status", "submitted"))
    computed_cost = cost_pusd if cost_pusd is not None else price * size
    return OrderResult(
        outcome=outcome,
        token_id=token_id,
        side=side,
        price=price,
        size=size,
        cost_pusd=computed_cost,
        order_id=str(order_id) if order_id is not None else None,
        status=status,
        raw=resp,
    )
