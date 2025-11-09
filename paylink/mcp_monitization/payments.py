"""
Payment enforcement utilities for PayLink MCP monetization workflows.
"""

from __future__ import annotations

import functools
import logging
import os
from contextvars import ContextVar
from typing import Any, Awaitable, Callable, Dict

import httpx
from mcp.types import TextContent

try:
    from dotenv import load_dotenv

    load_dotenv(override=True)
except Exception:
    # It's fine if python-dotenv is unavailable; environment variables can be
    # supplied through other means.
    pass

logger = logging.getLogger(__name__)

DEFAULT_WALLET_BASE_URL = "http://localhost:3001"

WalletSource = (
    str | ContextVar[str] | Callable[[], str | None] | None
)  # type: ignore[valid-type]


class PaymentError(RuntimeError):
    """Raised when a wallet transfer cannot be completed."""


async def _perform_wallet_transfer(
    *,
    from_token: str,
    amount: float,
    currency: str,
) -> Dict[str, Any]:
    base_url = DEFAULT_WALLET_BASE_URL
    to_token = os.getenv("PAYMENT_TO_TOKEN")
    transfer_endpoint = os.getenv(
        "PAYMENT_TRANSFER_ENDPOINT", "/api/v1/wallets/transfer"
    )

    if not to_token:
        raise PaymentError("Missing PAYMENT_TO_TOKEN environment configuration.")

    url = f"{base_url.rstrip('/')}{transfer_endpoint}"
    payload = {
        "from_token": from_token,
        "to_token": to_token,
        "amount": amount,
        "currency": currency,
    }

    logger.info(
        "Initiating wallet transfer of %s %s from %s to %s",
        amount,
        currency,
        from_token,
        to_token,
    )

    timeout = httpx.Timeout(10.0, read=20.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=payload)

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error("Wallet transfer HTTP error: %s", exc)
        raise PaymentError("Wallet transfer failed due to HTTP error.") from exc

    try:
        data = response.json()
    except ValueError as exc:
        logger.error("Wallet transfer returned invalid JSON: %s", exc)
        raise PaymentError("Wallet transfer returned invalid response.") from exc

    if not data.get("success"):
        logger.error("Wallet transfer failed: %s", data)
        raise PaymentError(data.get("message") or "Wallet transfer reported failure.")

    logger.info("Wallet transfer successful: %s", data.get("data"))
    return data


def require_payment(
    tool_costs: Dict[str, float],
    agent_wallet_address: WalletSource = None,
) -> Callable[
    [Callable[..., Awaitable[list[TextContent]]]],
    Callable[..., Awaitable[list[TextContent]]],
]:
    """
    Decorator that enforces payments before executing an MCP tool.

    Args:
        tool_costs: Mapping of tool names to their cost.
        agent_wallet_address: Wallet address/context source. Can be a context
            variable, a callable returning the current wallet string, or a fixed
            string.
    """

    def decorator(
        func: Callable[..., Awaitable[list[TextContent]]],
    ) -> Callable[..., Awaitable[list[TextContent]]]:
        @functools.wraps(func)
        async def wrapper(tool_name: str, arguments: Dict[str, Any]):
            cost = tool_costs.get(tool_name)

            if isinstance(agent_wallet_address, ContextVar):
                wallet_connection = agent_wallet_address.get(None)
            elif callable(agent_wallet_address):
                wallet_connection = agent_wallet_address()
            else:
                wallet_connection = agent_wallet_address

            if cost is not None:
                if not wallet_connection:
                    logger.warning(
                        "Payment required for '%s' but no wallet connection found.",
                        tool_name,
                    )
                    raise PaymentError(
                        "Missing wallet connection for payment validation."
                    )

                currency = os.getenv("PAYMENT_CURRENCY", "TRX")
                try:
                    await _perform_wallet_transfer(
                        from_token=wallet_connection,
                        amount=float(cost),
                        currency=currency,
                    )
                except PaymentError:
                    raise
                except Exception as exc:  # pragma: no cover - defensive
                    logger.exception("Unexpected error during wallet transfer.")
                    raise PaymentError(
                        "Unexpected error during wallet transfer."
                    ) from exc
            else:
                logger.debug("No payment required for '%s'", tool_name)

            return await func(tool_name, arguments)

        return wrapper

    return decorator

