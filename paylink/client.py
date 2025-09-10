# paylink/client.py
import asyncio
from typing import List, Dict, Any, Optional

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


class PayLink:
    """
    Python SDK for interacting with PayLink MCP servers.
    """

    def __init__(self, base_url: str = "http://0.0.0.0:5002/mcp"):
        self.base_url = base_url

    async def list_tools(self) -> List[str]:
        """
        List all available tools from the MCP server.
        Returns a list of tool.
        """
        async with streamablehttp_client(self.base_url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools = await session.list_tools()
                return tools

    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """
        Call a specific tool exposed by the MCP server.
        """
        async with streamablehttp_client(self.base_url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                # call_tool returns the raw tool response object from the mcp package
                result = await session.call_tool(tool_name, args)
                return result

