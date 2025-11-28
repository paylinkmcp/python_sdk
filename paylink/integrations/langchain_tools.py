"""
LangChain integration for PayLink.

Usage:

    from paylink.integrations.langchain_tools import PayLinkTools

    llm = init_chat_model(model="gpt-4o-mini", temperature=0)
    paylink_client = PayLinkTools(api_key="...")
    payment_tools = paylink_client.list_tools()
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, Dict, List, Optional

from .._sync import run_sync
from ..async_client import AsyncPayLink


def _get_structured_tool_cls():
    """
    Import LangChain's StructuredTool lazily so langchain-core is optional.
    """
    try:
        module = import_module("langchain_core.tools")
        return getattr(module, "StructuredTool")
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "langchain-core is required to use paylink.integrations.langchain_tools. "
            "Install it with `pip install langchain-core`."
        ) from exc


def _build_structured_tool(
    structured_cls, 
    client: AsyncPayLink, 
    name: str, 
    description: str,
    input_schema: Optional[Dict[str, Any]] = None
):
    """
    Helper to create one StructuredTool, avoids closure bugs in loops.
    """

    async def _arun(**kwargs: Any) -> Any:
        return await client.call_tool(name, kwargs)

    def _run(**kwargs: Any) -> Any:
        return run_sync(client.call_tool(name, kwargs))

    # If we have an input schema, use it to create the tool with proper parameter definitions
    if input_schema:
        try:
            # Try to import pydantic for schema conversion
            from pydantic import create_model, Field
            
            # Extract properties and required fields from the schema
            properties = input_schema.get("properties", {})
            required = input_schema.get("required", [])
            
            # Create field definitions for Pydantic
            field_definitions = {}
            for prop_name, prop_schema in properties.items():
                prop_type = str  # Default to str
                prop_description = prop_schema.get("description", "")
                
                # Map JSON schema types to Python types
                json_type = prop_schema.get("type", "string")
                if json_type == "integer":
                    prop_type = int
                elif json_type == "number":
                    prop_type = float
                elif json_type == "boolean":
                    prop_type = bool
                elif json_type == "array":
                    prop_type = list
                elif json_type == "object":
                    prop_type = dict
                
                # Create Field with description and constraints
                field_kwargs = {"description": prop_description}
                
                # Add validation constraints if present
                if "pattern" in prop_schema:
                    field_kwargs["pattern"] = prop_schema["pattern"]
                if "maxLength" in prop_schema:
                    field_kwargs["max_length"] = prop_schema["maxLength"]
                if "minLength" in prop_schema:
                    field_kwargs["min_length"] = prop_schema["minLength"]
                
                # Make field optional if not in required list
                if prop_name not in required:
                    field_definitions[prop_name] = (Optional[prop_type], Field(default=None, **field_kwargs))
                else:
                    field_definitions[prop_name] = (prop_type, Field(**field_kwargs))
            
            # Create Pydantic model from schema
            ArgsModel = create_model(f"{name}Args", **field_definitions)
            
            return structured_cls(
                func=_run,
                coroutine=_arun,
                name=name,
                description=description,
                args_schema=ArgsModel,
            )
        except (ImportError, Exception):
            # Fallback if pydantic is not available or schema creation fails
            # This won't have the proper schema, but will still work
            return structured_cls.from_function(
                func=_run,
                coroutine=_arun,
                name=name,
                description=description,
            )
    
    # No input schema provided, use from_function
    return structured_cls.from_function(
        func=_run,
        coroutine=_arun,
        name=name,
        description=description,
    )


class PayLinkTools:
    """
    LangChain-ready adapter that exposes all tools registered on the PayLink MCP server.

    - Uses AsyncPayLink under the hood.
    - Exposes a simple sync method: list_tools().
    """

    def __init__(
        self,
        base_url: str = "http://3.107.114.80:5002/mcp",
        api_key: Optional[str] = None,
        tracing: Optional[str] = None,
        project: Optional[str] = None,
        payment_provider: Optional[List[str]] = None,
        required_headers: Optional[List[str]] = None,
    ) -> None:
        self._client = AsyncPayLink(
            base_url=base_url,
            api_key=api_key,
            tracing=tracing,
            project=project,
            payment_provider=payment_provider,
            required_headers=required_headers,
        )
        self._StructuredTool = _get_structured_tool_cls()

    # ---------- public sync API ----------

    def list_tools(self) -> List[Any]:
        """
        Return a list of LangChain StructuredTool objects.

        This is synchronous by design so you can write:

            payment_tools = PayLinkTools(...).list_tools()
        """
        return run_sync(self._list_tools_async())

    # ---------- internal async helper ----------

    async def _list_tools_async(self) -> List[Any]:
        server_tools = await self._client.list_tools()
        StructuredTool = self._StructuredTool

        tools: List[Any] = []
        for tool_desc in server_tools:
            name = getattr(tool_desc, "name", "")
            description = getattr(tool_desc, "description", "") or ""
            
            # Extract inputSchema if available
            input_schema = None
            if hasattr(tool_desc, "inputSchema"):
                input_schema = tool_desc.inputSchema
            elif hasattr(tool_desc, "input_schema"):
                input_schema = tool_desc.input_schema
            
            # Convert inputSchema to dict if it's not already
            if input_schema and not isinstance(input_schema, dict):
                # Try to convert if it's a Pydantic model or similar
                if hasattr(input_schema, "model_json_schema"):
                    input_schema = input_schema.model_json_schema()
                elif hasattr(input_schema, "dict"):
                    input_schema = input_schema.dict()
                elif hasattr(input_schema, "__dict__"):
                    input_schema = input_schema.__dict__
            
            tools.append(
                _build_structured_tool(
                    structured_cls=StructuredTool,
                    client=self._client,
                    name=name,
                    description=description,
                    input_schema=input_schema,
                )
            )
        return tools
