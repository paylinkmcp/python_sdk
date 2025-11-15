# PayLink Python SDK

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)

Python SDK for PayLink - AI-Powered Payment Integration Framework

## Installation

```bash
pip install paylink
```

### Installing from the local repository (editable)

If you're working on the SDK and want downstream projects to pick up changes automatically:

```bash
pip install -e /Users/jameskanyiri/PAYLINK/python_sdk
```

When using a virtual environment, make sure it is activated before running the command. Any edits made to the SDK will be immediately reflected in the projects where it is installed in editable mode.

If you are using [uv](https://github.com/astral-sh/uv), the equivalent command is:

```bash
uv pip install --editable /Users/jameskanyiri/PAYLINK/python_sdk
```

## Quick Start

```python
import asyncio
from paylink import MpesaTools, McpMonitizationAdapter


async def use_mpesa_tools():
    # Uses default PayLink MCP server URL
    client = MpesaTools()
    tools = await client.list_tools()
    print("Available M-Pesa tools:", tools)

    if "stk_push" in tools:
        result = await client.call_tool(
            "stk_push",
            {
                "amount": "100",
                "phone_number": "254712345678",
                "account_reference": "ORDER123",
                "transaction_desc": "Payment",
            },
        )
        print("Payment result:", result)


async def use_custom_mcp_adapter():
    # Requires the caller to provide a concrete MCP server URL as well as
    # wallet and transport configuration. The wallet connection string will be
    # forwarded as a request header (`WALLET_CONNECTION_STRING`).
    adapter = McpMonitizationAdapter(
        mcp_server_url="https://your-mcp-server.example.com/mcp",
        wallet_connection_string="postgresql://wallet-user:secret@db/wallet",
        transport="grpc",
    )
    print("Custom MCP tools:", await adapter.list_tools())


if __name__ == "__main__":
    asyncio.run(use_mpesa_tools())
    asyncio.run(use_custom_mcp_adapter())
```

## API Reference

### PayLink Class

#### `__init__(base_url: str = "http://3.107.114.80:5002/mcp")`

Initialize the PayLink client.

**Parameters:**

- `base_url` (str): The base URL of your PayLink MCP server

#### `async list_tools() -> List[str]`

List all available tools from the MCP server.

**Returns:**

- `List[str]`: A list of available tool names

#### `async call_tool(tool_name: str, args: Dict[str, Any]) -> Any`

Call a specific tool exposed by the MCP server.

**Parameters:**

- `tool_name` (str): The name of the tool to call
- `args` (Dict[str, Any]): Arguments to pass to the tool

**Returns:**

- `Any`: The result from the tool execution

## Examples

### STK Push Payment

```python
import asyncio
from paylink import MpesaTools


async def stk_push_example():
    client = MpesaTools(base_url="http://your-server:5002/mcp")

    result = await client.call_tool(
        "stk_push",
        {
            "amount": "100",
            "phone_number": "254712345678",
            "account_reference": "ORDER123",
            "transaction_desc": "Test Payment",
        },
    )

    print(f"Payment initiated: {result}")


asyncio.run(stk_push_example())
```

### List Available Tools

```python
import asyncio
from paylink import McpMonitizationAdapter


async def list_tools_example():
    adapter = McpMonitizationAdapter(
        mcp_server_url="https://your-mcp-server.example.com/mcp",
        wallet_connection_string="postgresql://wallet-user:secret@db/wallet",
        transport="grpc",
    )
    tools = await adapter.list_tools()

    for tool in tools:
        print(f"Available tool: {tool}")


asyncio.run(list_tools_example())
```

## Requirements

- Python 3.10+
- PayLink MCP server running and accessible

## Dependencies

- `mcp[cli]>=1.13.1` - Model Context Protocol client

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support and questions, please open an issue on the [GitHub repository](https://github.com/yourusername/paylink/issues).
