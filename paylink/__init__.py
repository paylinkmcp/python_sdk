"""
PayLink Python SDK

A Python SDK for interacting with PayLink MCP (Model Context Protocol) servers.
"""

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

from .client import PayLink               # Sync client
from .async_client import AsyncPayLink    # Async client

# Alias for convenience
Paylink = PayLink

# ---------------------------------------------------------------------------
# Package metadata
# ---------------------------------------------------------------------------

__version__ = "0.4.2"
__author__ = "PayLink"
__email__ = "paylinkmcp@gmail.com"

__all__ = [
    "PayLink",
    "Paylink",  # Alias
    "AsyncPayLink"
]
