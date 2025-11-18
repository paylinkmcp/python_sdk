# async_client.py
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, Optional

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from .config import PayLinkConfig  # internal use only


class AsyncPayLink:
    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        tracing: Optional[str] = None,
        project: Optional[str] = None,
        payment_provider: Optional[list[str]] = None,
        required_headers: Optional[list[str]] = None,
        config: Optional[PayLinkConfig] = None,  # still allowed for advanced internal usage
    ):
        if config is not None:
            self._config = config
        else:
            self._config = PayLinkConfig.resolve(
                base_url= base_url or "http://3.107.114.80:5002/mcp",
                api_key=api_key,
                tracing=tracing,
                project=project,
                payment_provider=payment_provider,
                required_headers=required_headers,
            )

        self.base_url = self._config.base_url
        self.headers = self._config.headers

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[ClientSession]:
        async with streamablehttp_client(self.base_url, headers=self.headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session

    async def list_tools(self):
        async with self.connect() as session:
            result = await session.list_tools()
            tools = result.tools
            
            return tools

    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        async with self.connect() as session:
            result = await session.call_tool(tool_name, args)
            
            return result
