from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from .config import PayLinkConfig


class PayLink:
    """
    Python SDK for interacting with PayLink MCP servers.
    """

    def __init__(
        self,
        base_url: str = "http://0.0.0.0:5002/mcp",
        api_key: Optional[str] = None,
        tracing: Optional[str] = None,
        project: Optional[str] = None,
        payment_provider: Optional[List[str]] = None,
        required_headers: Optional[List[str]] = None,
        *,
        config: Optional[PayLinkConfig] = None,
    ):
        if config is not None:
            resolved_config = config
        else:
            resolved_config = PayLinkConfig.resolve(
                base_url=base_url,
                api_key=api_key,
                tracing=tracing,
                project=project,
                payment_provider=payment_provider,
                required_headers=required_headers,
            )

        self.base_url = resolved_config.base_url
        self.api_key = resolved_config.api_key
        self.tracing = resolved_config.tracing
        self.project = resolved_config.project
        self.payment_provider = resolved_config.payment_provider
        self.headers: Dict[str, str] = resolved_config.headers
        self.mpesa_settings: Dict[str, Optional[str]] = resolved_config.mpesa_settings_dict()
        self.monitization_settings: Dict[str, str] = resolved_config.monitization_settings_dict()
        self._required_headers = resolved_config.required_headers

        self._validate_headers()

    def _validate_headers(self) -> None:
        """
        Validate that all required headers are present and not empty.
        """
        if not self._required_headers:
            return
        for key in self._required_headers:
            if key not in self.headers or not self.headers[key]:
                raise ValueError(f"Missing required header: {key}")

    @asynccontextmanager
    async def connect(self):
        """
        Async context manager to connect to the MCP server using streamable HTTP.
        """
        async with streamablehttp_client(self.base_url, headers=self.headers) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                yield session

    async def list_tools(self):
        """
        List all available tools from the MCP server.
        Returns a list of ToolDescription objects.
        """
        async with self.connect() as session:
            tools_result = await session.list_tools()
            return tools_result.tools

    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """
        Call a specific tool exposed by the MCP server.
        """
        async with self.connect() as session:
            # Confirm tool exists from the server's tool list
            tools_result = await session.list_tools()
            tool = next((t for t in tools_result.tools if t.name == tool_name), None)
            if not tool:
                raise ValueError(f"Tool '{tool_name}' not found in server's tool list.")

            result = await session.call_tool(tool_name, args)
            return result


