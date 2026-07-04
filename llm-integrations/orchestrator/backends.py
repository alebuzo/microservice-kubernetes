"""Architecture backends for the shared agent orchestrator.

Both backends expose the same tiny interface — `.tools` (a list of Anthropic
tool-use schema dicts) and `async def call_tool(name, arguments) -> dict` —
so `agent.py`'s conversation loop is 100% identical regardless of which
architecture (Function Calling or MCP) is driving the tool calls. This is
what lets the orchestrator switch via a single `--mode` flag while keeping
model/temperature/system prompt/conversation logic as a controlled constant.
"""

import asyncio
import json
import sys
from contextlib import AbstractAsyncContextManager
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from function_calling.client import call_tool as fc_call_tool
from function_calling.tools import TOOL_DEFINITIONS as FC_TOOL_DEFINITIONS


class FunctionCallingBackend(AbstractAsyncContextManager):
    """Backend that dispatches tool calls directly via HTTP (no MCP)."""

    def __init__(self) -> None:
        self.tools: list[dict] = FC_TOOL_DEFINITIONS

    async def __aenter__(self) -> "FunctionCallingBackend":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        return None

    async def call_tool(self, name: str, arguments: dict) -> dict:
        # fc_call_tool does blocking HTTP I/O (httpx sync client); run it off
        # the event loop thread so it behaves like the MCP backend's await.
        return await asyncio.to_thread(fc_call_tool, name, arguments)


class McpBackend(AbstractAsyncContextManager):
    """Backend that dispatches tool calls through a local MCP server
    (`mcp_server/server.py`) over a stdio subprocess transport.
    """

    def __init__(self) -> None:
        self.tools: list[dict] = []
        self._stdio_ctx = None
        self._session_ctx = None
        self._session: ClientSession | None = None

    async def __aenter__(self) -> "McpBackend":
        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_server.server"],
        )
        self._stdio_ctx = stdio_client(server_params)
        read, write = await self._stdio_ctx.__aenter__()
        self._session_ctx = ClientSession(read, write)
        self._session = await self._session_ctx.__aenter__()
        await self._session.initialize()

        discovered = await self._session.list_tools()
        self.tools = [
            {
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.inputSchema,
            }
            for tool in discovered.tools
        ]
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        if self._session_ctx is not None:
            await self._session_ctx.__aexit__(*exc_info)
        if self._stdio_ctx is not None:
            await self._stdio_ctx.__aexit__(*exc_info)

    async def call_tool(self, name: str, arguments: dict) -> dict:
        assert self._session is not None, "McpBackend used outside 'async with'"
        result = await self._session.call_tool(name, arguments)
        text = "".join(block.text for block in result.content if block.type == "text")
        try:
            return json.loads(text)
        except ValueError:
            return {"raw": text}


def make_backend(mode: str) -> AbstractAsyncContextManager:
    if mode == "function_calling":
        return FunctionCallingBackend()
    if mode == "mcp":
        return McpBackend()
    raise ValueError(f"Unknown mode: {mode!r}. Expected 'function_calling' or 'mcp'.")
