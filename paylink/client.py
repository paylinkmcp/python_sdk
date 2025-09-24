import json
import os
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

try:
    from dotenv import load_dotenv

    load_dotenv(override=True)
except Exception:
    # It's okay if python-dotenv is not installed; env vars can be provided by the environment
    pass


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
    ):
        self.base_url = base_url

        # Initialize headers
        self.headers: Dict[str, str] = {}

        # Config from args or environment
        self.api_key = api_key or os.getenv("PAYLINK_API_KEY")
        self.tracing = (tracing or os.getenv("PAYLINK_TRACING") or "").strip()
        self.project = project or os.getenv("PAYLINK_PROJECT")

        # PAYMENT_PROVIDER expected to be a JSON array in env (e.g., ["mpesa"])
        if payment_provider is not None:
            self.payment_provider = payment_provider
        else:
            providers_raw = os.getenv("PAYMENT_PROVIDER", "[]")
            try:
                parsed = json.loads(providers_raw)
                self.payment_provider = parsed if isinstance(parsed, list) else []
            except json.JSONDecodeError:
                self.payment_provider = []

        # Assemble headers
        if self.api_key:
            self.headers["PAYLINK_API_KEY"] = self.api_key
        if self.tracing and self.tracing.lower() == "enabled":
            self.headers["PAYLINK_TRACING"] = "enabled"
        if self.project:
            self.headers["PAYLINK_PROJECT"] = self.project
        if self.payment_provider:
            self.headers["PAYMENT_PROVIDER"] = json.dumps(self.payment_provider)

        # M-Pesa settings if configured
        self.mpesa_settings: Dict[str, Optional[str]] = {}
        if any(str(p).lower() == "mpesa" for p in (self.payment_provider or [])):
            self.mpesa_settings = {
                "MPESA_BUSINESS_SHORTCODE": os.getenv("MPESA_BUSINESS_SHORTCODE"),
                "MPESA_CONSUMER_SECRET": os.getenv("MPESA_CONSUMER_SECRET"),
                "MPESA_CONSUMER_KEY": os.getenv("MPESA_CONSUMER_KEY"),
                "MPESA_CALLBACK_URL": os.getenv("MPESA_CALLBACK_URL"),
                "MPESA_PASSKEY": os.getenv("MPESA_PASSKEY"),
                "MPESA_BASE_URL": os.getenv("MPESA_BASE_URL"),
            }

            required = [
                "MPESA_BUSINESS_SHORTCODE",
                "MPESA_CONSUMER_SECRET",
                "MPESA_CONSUMER_KEY",
                "MPESA_CALLBACK_URL",
                "MPESA_PASSKEY",
                "MPESA_BASE_URL",
            ]
            missing = [k for k in required if not self.mpesa_settings.get(k)]
            if missing:
                raise ValueError(f"Missing M-Pesa settings: {', '.join(missing)}")

            # Expose M-Pesa settings in headers
            for key, value in self.mpesa_settings.items():
                if value is not None:
                    self.headers[key] = value

        self._validate_headers()

    def _validate_headers(self) -> None:
        """
        Validate that all required headers are present and not empty.
        """
        required_headers = [
            "PAYLINK_API_KEY",
            "PAYLINK_PROJECT",
            "PAYLINK_TRACING",
            "PAYMENT_PROVIDER",
        ]
        for key in required_headers:
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
