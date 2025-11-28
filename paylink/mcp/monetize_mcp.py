"""
Payment enforcement utilities for PayLink MCP monetization workflows.

This module is intended for MCP server authors. It provides a `require_payment`
decorator that you can apply to your `@app.call_tool()` handler to enforce
wallet-based payments before executing a tool.

Terminology:

- Agent wallet connection string:
    The caller's wallet (client / agent) connection string. This is typically
    sent in the `WALLET_CONNECTION_STRING` HTTP header by the SDK or client.

- MCP wallet connection string:
    The MCP server's wallet connection string that receives funds. This is
    configured via the MCP_WALLET_CONNECTION_STRING environment variable.
"""

from __future__ import annotations

import functools
import logging
import os
from contextvars import ContextVar
from typing import Any, Awaitable, Callable, Dict

import httpx
from mcp.types import TextContent

from .wallet_context import get_agent_wallet_connection_string

from dotenv import load_dotenv

load_dotenv(override=True)

logger = logging.getLogger(__name__)

# Default wallet API base URL, can be overridden by env if needed.
DEFAULT_WALLET_BASE_URL = "https://wallet.paylinkai.app"
# DEFAULT_WALLET_BASE_URL = "http://localhost:3001"

MCP_WALLET_CONNECTION_STRING = "MCP_WALLET_CONNECTION_STRING"

AgentWalletConnectionSource = (
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
    """
    Perform a wallet transfer using the PayLink wallet API.

    - from_token: agent wallet connection string (client/agent)
    - to_token: MCP wallet connection string (server), from MCP_WALLET_CONNECTION_STRING

    Env variables used:
        - MCP_WALLET_CONNECTION_STRING (required)
        - PAYMENT_TRANSFER_ENDPOINT (optional, default "/api/v1/wallets/transfer")
        - PAYMENT_WALLET_BASE_URL (optional, overrides DEFAULT_WALLET_BASE_URL)
    """
    base_url = os.getenv("PAYMENT_WALLET_BASE_URL", DEFAULT_WALLET_BASE_URL)
    to_token = os.getenv(MCP_WALLET_CONNECTION_STRING)
    transfer_endpoint = os.getenv(
        "PAYMENT_TRANSFER_ENDPOINT", "/api/v1/wallets/transfer"
    )

    if not to_token:
        raise PaymentError(
            f"Missing {MCP_WALLET_CONNECTION_STRING} environment configuration "
            "for MCP wallet connection string."
        )

    url = f"{base_url}{transfer_endpoint}"
    payload = {
        "from_token": from_token,
        "to_token": to_token,
        "amount": amount,
        "currency": currency,
    }

    logger.info(
        "Initiating wallet transfer of %s %s from agent wallet '%s' to MCP wallet '%s'",
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
    tool_costs: Dict[str, float]
) -> Callable[
    [Callable[..., Awaitable[list[TextContent]]]],
    Callable[..., Awaitable[list[TextContent]]],
]:
    """
    Decorator that enforces payments before executing an MCP tool.

    Args:
        tool_costs:
            Mapping of tool names to their cost (in PAYMENT_CURRENCY units).
            Example: {"add": 0.01, "subtract": 0.02}


            Can be one of:
                - a ContextVar[str] that holds the current agent wallet connection string
                - a callable returning str | None
                - a fixed string
                - None (no wallet available)
    """

    def decorator(
        func: Callable[..., Awaitable[list[TextContent]]],
    ) -> Callable[..., Awaitable[list[TextContent]]]:
        @functools.wraps(func)
        async def wrapper(tool_name: str, arguments: Dict[str, Any]):
            cost = tool_costs.get(tool_name)

            # # Resolve agent wallet connection string from internal request context
            wallet_connection = get_agent_wallet_connection_string()

            if cost is not None:
                if not wallet_connection:
                    logger.warning(
                        "Payment required for '%s' but no agent wallet connection string found.",
                        tool_name,
                    )
                    raise PaymentError(
                        "Missing agent wallet connection string for payment validation."
                    )

                currency = os.getenv("PAYMENT_CURRENCY", "TRX")
                try:
                    await _perform_wallet_transfer(
                        from_token=wallet_connection,
                        amount=float(cost),
                        currency=currency,
                    )
                except PaymentError:
                    # Bubble up well-formed payment errors
                    raise
                except Exception as exc:  # pragma: no cover - defensive
                    logger.exception("Unexpected error during wallet transfer.")
                    raise PaymentError(
                        "Unexpected error during wallet transfer."
                    ) from exc
            else:
                logger.debug("No payment required for '%s'", tool_name)

            # If payment was successful or not required, execute the tool
            return await func(tool_name, arguments)

        return wrapper

    return decorator
