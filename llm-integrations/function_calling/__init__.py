"""Function Calling integration for the Function Calling vs MCP experiment.

This package exposes the same set of operations as the MCP server
(`llm-integrations/mcp_server/`) but as plain Anthropic tool-use schemas plus
a synchronous HTTP dispatch function, so the shared orchestrator can select
between architectures via a single flag (`--mode function_calling`).
"""

from .tools import TOOL_DEFINITIONS
from .client import call_tool

__all__ = ["TOOL_DEFINITIONS", "call_tool"]
