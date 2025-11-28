from __future__ import annotations

import logging
from contextvars import ContextVar, Token
from typing import Optional

from starlette.types import Scope

logger = logging.getLogger(__name__)

# Internal context var that holds the agent's wallet connection string
_AGENT_WALLET_CTX: ContextVar[Optional[str]] = ContextVar(
    "agent_wallet_connection_string", default=None
)


def extract_agent_wallet_from_scope(
    scope: Scope,
    header_name: str = "wallet_connection_string",
) -> Optional[str]:
    """
    Extract the agent wallet connection string from the HTTP scope headers.

    This hides the low-level header iteration / decoding from the server author.
    """
    raw = scope.get("headers", []) or []

    for key_bytes, value_bytes in raw:
        if key_bytes.decode().lower() == header_name.lower():
            value = value_bytes.decode()
            logger.debug("Extracted %s from headers: %s", header_name, value)
            return value

    logger.debug("No %s header found in request", header_name)
    return None


def set_agent_wallet_from_scope(
    scope: Scope,
    header_name: str = "wallet_connection_string",
) -> Token | None:
    """
    Read the agent wallet connection string from the scope and store it
    in the internal ContextVar for the duration of this request.

    Returns a Token that can be used to reset the ContextVar afterwards.
    """
    value = extract_agent_wallet_from_scope(scope, header_name=header_name)
    if value is None:
        return None

    token: Token = _AGENT_WALLET_CTX.set(value)
    return token


def reset_agent_wallet(token: Token | None) -> None:
    """
    Reset the internal ContextVar if a token was set.
    """
    if token is not None:
        _AGENT_WALLET_CTX.reset(token)


def get_agent_wallet_connection_string(default: Optional[str] = None) -> Optional[str]:
    """
    Get the current agent wallet connection string for this request.

    This is what tools / decorators should call when they need to know which
    wallet to charge.
    """
    return _AGENT_WALLET_CTX.get(default)
