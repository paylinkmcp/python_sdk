# client.py
from __future__ import annotations

from typing import Any, Dict, Optional

from ._sync import run_sync
from .async_client import AsyncPayLink
from .config import PayLinkConfig 


class PayLink:
    """
    Sync-first PayLink client.
    """

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        tracing: Optional[str] = None,
        project: Optional[str] = None,
        payment_provider: Optional[list[str]] = None,
        required_headers: Optional[list[str]] = None,
        config: Optional[PayLinkConfig] = None,
    ):
        if config is not None:
            self._config = config
        else:
            self._config = PayLinkConfig.resolve(
                base_url=base_url or "http://3.107.114.80:5002/mcp",
                api_key=api_key,
                tracing=tracing,
                project=project,
                payment_provider=payment_provider,
                required_headers=required_headers,
            )

        self._async = AsyncPayLink(config=self._config)

    def list_tools(self):
        return run_sync(self._async.list_tools())

    def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        return run_sync(self._async.call_tool(tool_name, args))
