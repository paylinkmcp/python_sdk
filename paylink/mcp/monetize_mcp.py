"""
Payment enforcement utilities for PayLink MCP monetization workflows.

This module is intended for MCP server authors. It provides a `require_payment`
decorator that you can apply to your `@app.call_tool()` handler to enforce
wallet-based payments around a tool call.

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
import json
import logging
import os
from typing import Any, Awaitable, Callable, Dict, TypedDict, Union

import httpx
from mcp.types import TextContent
from dotenv import load_dotenv

from .wallet_context import get_agent_wallet_connection_string

load_dotenv(override=True)

logger = logging.getLogger(__name__)

# Default wallet API base URL, can be overridden by env if needed.
# DEFAULT_WALLET_BASE_URL = "https://wallet.paylinkai.app"
DEFAULT_WALLET_BASE_URL = "http://localhost:3001"

# Default evaluator base URL
# DEFAULT_EVALUATOR_BASE_URL = "http://127.0.0.1:2024"
DEFAULT_EVALUATOR_BASE_URL = "https://evaluator.paylinkai.app"

MCP_WALLET_CONNECTION_STRING = "MCP_WALLET_CONNECTION_STRING"


class PaymentError(RuntimeError):
    """Raised when a wallet transfer cannot be completed."""


class ToolConfig(TypedDict, total=False):
    """Optional configuration for a single MCP tool."""
    base_cost: float
    require_evaluation: bool


ToolConfigEntry = Union[float, ToolConfig]


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



async def _evaluate_tool_result(
    *,
    tool_name: str,
    tool_input: Dict[str, Any],
    tool_result: list[TextContent],
) -> Dict[str, Any]:
    """
    Evaluate a tool result using the PayLink Evaluator API.

    Args:
        tool_name: Name of the tool that was called
        tool_input: The input arguments passed to the tool
        tool_result: The result returned by the tool (list of TextContent)

    Returns:
        Dictionary containing the evaluation response

    Env variables used:
        - EVALUATOR_BASE_URL (optional, default "http://127.0.0.1:2024")
    """
    base_url = os.getenv("EVALUATOR_BASE_URL", DEFAULT_EVALUATOR_BASE_URL)
    url = f"{base_url}/evaluate"

    # Format tool_input as JSON string
    tool_input_str = json.dumps(tool_input)

    # Format tool_result as string representation
    tool_result_str = f"{tool_result}"

    payload = {
        "tool_name": tool_name,
        "tool_input": tool_input_str,
        "tool_result": tool_result_str,
    }

    logger.info(
        "Evaluating tool '%s' result via evaluator at %s",
        tool_name,
        url,
    )

    timeout = httpx.Timeout(10.0, read=20.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=payload)

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error("Evaluator HTTP error: %s", exc)
        raise PaymentError("Tool evaluation failed due to HTTP error.") from exc

    try:
        data = response.json()
    except ValueError as exc:
        logger.error("Evaluator returned invalid JSON: %s", exc)
        raise PaymentError("Evaluator returned invalid response.") from exc

    logger.info("Tool evaluation response: %s", data)
    return data


def require_payment(
    tool_configs: Dict[str, ToolConfigEntry],
) -> Callable[
    [Callable[..., Awaitable[list[TextContent]]]],
    Callable[..., Awaitable[list[TextContent]]],
]:
    """
    Decorator that enforces payments around executing an MCP tool.

    Args:
        tool_configs:
            Mapping of tool names to either:
              - a simple float cost, e.g. {"add": 0.01}
              - a config dict, e.g. {"subtract": {"base_cost": 0.02, "require_evaluation": True}}

            Examples:
                tool_configs = {
                    "add": 0.10,  # no evaluation, just charge
                    "subtract": {
                        "base_cost": 0.10,
                        "require_evaluation": True,
                    },
                }
    """

    def decorator(
        func: Callable[..., Awaitable[list[TextContent]]],
    ) -> Callable[..., Awaitable[list[TextContent]]]:
        @functools.wraps(func)
        async def wrapper(tool_name: str, arguments: Dict[str, Any]) -> list[TextContent]:
            config = tool_configs.get(tool_name)

            if isinstance(config, dict):
                base_cost = float(config.get("base_cost", 0.0))
                require_evaluation = bool(config.get("require_evaluation", False))
            elif isinstance(config, (int, float)):
                base_cost = float(config)
                require_evaluation = False
            else:
                base_cost = None
                require_evaluation = False

            # First execute the tool to get the result
            tool_result = await func(tool_name, arguments)

            # If no cost is configured, just return the result
            if base_cost is None:
                logger.debug("No payment required for '%s'", tool_name)
                return tool_result

            # ------------------------------------------------------------
            # If cost is configured, means that we need to perform  a wallet transfer
            # This means we need to start by resolving the agent wallet connection string
            # and then performing the wallet transfer
            # ------------------------------------------------------------

            # Resolve agent wallet connection string from internal request context
            wallet_connection = get_agent_wallet_connection_string()
            if not wallet_connection:
                logger.warning(
                    "Payment required for '%s' but no agent wallet connection string found.",
                    tool_name,
                )
                raise PaymentError(
                    "Missing agent wallet connection string for payment validation."
                )

            # If wallet connection string is found, then before transferring the funds, we need to check if the evaluation is enabled
            # This will help with dynamically determining the cost of the tool call

            if require_evaluation:
                logger.info("Evaluating tool '%s' before charging.", tool_name)
                try:
                    
                    evaluation = await _evaluate_tool_result(
                        tool_name=tool_name,
                        tool_input=arguments,
                        tool_result=tool_result,
                    )


                    # Log evaluation details
                    quality_score = evaluation.get("quality_score")
                    reason = evaluation.get("reason")
                    issues = evaluation.get("issues", [])
                    
                    logger.info(
                        "Tool evaluation for '%s': is_acceptable=%s, quality_score=%s",
                        tool_name,
                        evaluation.get("is_acceptable"),
                        quality_score,
                    )
                    if reason:
                        logger.debug("Evaluation reason: %s", reason)
                    if issues:
                        logger.warning("Evaluation found issues: %s", issues)
                    
                    # Check if evaluation indicates the result is acceptable
                    if not evaluation.get("is_acceptable", False):
                        error_msg = "Tool result failed evaluation; not charging."
                        if reason:
                            error_msg += f" Reason: {reason}"
                        if issues:
                            error_msg += f" Issues: {issues}"
                        raise PaymentError(error_msg)
                except PaymentError:
                    # Bubble up payment errors from evaluation
                    raise
                except Exception as exc:
                    logger.exception("Unexpected error during tool evaluation.")
                    raise PaymentError(
                        "Unexpected error during tool evaluation."
                    ) from exc

            currency = os.getenv("PAYMENT_CURRENCY", "TRX")

            try:
                await _perform_wallet_transfer(
                    from_token=wallet_connection,
                    amount=base_cost,
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

            # Payment succeeded → return the tool result to the agent
            return tool_result

        return wrapper

    return decorator
