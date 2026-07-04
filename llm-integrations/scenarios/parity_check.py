"""Automated functional-parity check between Function Calling and MCP.

Verifies the `integration-parity-check` requirement from `plan.md`: both
architectures must expose the same operations, with the same semantics and
parameters, and must behave identically against a real running cluster.
Unlike `function_calling/manual_test.py` / `mcp_server/manual_test.py`
(which each check one architecture in isolation), this script runs BOTH
architectures against the exact same test cases and diffs the results
directly, so a divergence between them is caught automatically instead of
relying on manual comparison.

Two checks are performed:
  1. Tool schema parity — same tool names, same required parameter names,
     between `function_calling/tools.py` (Anthropic `input_schema`) and the
     MCP server's `list_tools()` (FastMCP-generated `inputSchema`).
  2. Tool call parity — for a fixed list of (name, args) cases (2 valid +
     1 invalid per read operation, plus create_order valid/invalid), calls
     both architectures and asserts the results match. Both architectures
     delegate to the same `common/services.py` HTTP calls, so results should
     be identical except for server-generated ids (e.g. a fresh `create_order`
     call creates a new row each time) — those fields are excluded from the
     comparison instead of hardcoded, so the check stays meaningful after
     schema changes are applied (`schema_changes/apply.sh`), where a
     divergence is expected and is exactly what the experiment measures.

Run from `llm-integrations/` with the same port-forwards used throughout
this project active:
    kubectl port-forward svc/catalog  18081:8080
    kubectl port-forward svc/customer 18082:8080
    kubectl port-forward svc/order    18083:8080

Usage:
    cd llm-integrations
    source .venv/bin/activate
    python -m scenarios.parity_check
"""

import asyncio
import json
import sys
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from function_calling.client import call_tool as fc_call_tool
from function_calling.tools import TOOL_DEFINITIONS

# (tool name, arguments, keys to ignore when diffing the two results —
# server-generated/non-deterministic fields such as auto-increment ids)
CASES: list[tuple[str, dict, set[str]]] = [
    ("get_catalog_item", {"item_id": 1}, set()),
    ("get_catalog_item", {"item_id": 9999}, set()),  # expected error
    ("get_customer", {"customer_id": 1}, set()),
    ("get_customer", {"customer_id": 9999}, set()),  # expected error
    (
        "create_order",
        {"customer_id": 1, "order_lines": [{"item_id": 1, "count": 1}]},
        {"id"},  # a fresh order id is created on each call
    ),
    (
        "create_order",
        {"customer_id": 1, "order_lines": [{"item_id": 9999, "count": 1}]},
        set(),
    ),  # expected error, no id involved
]


def _strip_ignored(value: Any, ignore: set[str]) -> Any:
    if isinstance(value, dict):
        return {k: _strip_ignored(v, ignore) for k, v in value.items() if k not in ignore}
    if isinstance(value, list):
        return [_strip_ignored(v, ignore) for v in value]
    return value


def check_tool_schemas(mcp_tools: list) -> list[str]:
    """Compares tool names + required parameter names. Returns a list of
    human-readable mismatch descriptions (empty list == parity)."""
    problems: list[str] = []

    fc_by_name = {t["name"]: t for t in TOOL_DEFINITIONS}
    mcp_by_name = {t.name: t for t in mcp_tools}

    fc_names = set(fc_by_name)
    mcp_names = set(mcp_by_name)
    if fc_names != mcp_names:
        problems.append(
            f"Tool name mismatch: function_calling only={fc_names - mcp_names}, "
            f"mcp only={mcp_names - fc_names}"
        )

    for name in sorted(fc_names & mcp_names):
        fc_props = set(fc_by_name[name]["input_schema"].get("properties", {}))
        mcp_props = set(mcp_by_name[name].inputSchema.get("properties", {}))
        if fc_props != mcp_props:
            problems.append(
                f"'{name}' parameter mismatch: function_calling={fc_props}, mcp={mcp_props}"
            )

    return problems


async def run_mcp_case(session: ClientSession, name: str, args: dict) -> Any:
    result = await session.call_tool(name, args)
    text = "".join(block.text for block in result.content if block.type == "text")
    try:
        return json.loads(text)
    except ValueError:
        return text


async def main() -> int:
    server_params = StdioServerParameters(command=sys.executable, args=["-m", "mcp_server.server"])

    problems: list[str] = []

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            mcp_tools = (await session.list_tools()).tools

            print("== 1. Tool schema parity ==")
            schema_problems = check_tool_schemas(mcp_tools)
            if schema_problems:
                problems.extend(schema_problems)
                for p in schema_problems:
                    print(f"[MISMATCH] {p}")
            else:
                print(f"OK: {len(mcp_tools)} tools, same names and parameters in both architectures.")

            print("\n== 2. Tool call parity ==")
            for name, args, ignore in CASES:
                fc_result = fc_call_tool(name, args)
                mcp_result = await run_mcp_case(session, name, args)

                fc_norm = _strip_ignored(fc_result, ignore)
                mcp_norm = _strip_ignored(mcp_result, ignore)

                if fc_norm == mcp_norm:
                    print(f"[OK] {name}({args})")
                else:
                    msg = (
                        f"{name}({args}) diverged:\n"
                        f"  function_calling -> {fc_result}\n"
                        f"  mcp               -> {mcp_result}"
                    )
                    problems.append(msg)
                    print(f"[MISMATCH] {msg}")

    print()
    if problems:
        print(f"{len(problems)} parity problem(s) found.")
        return 1
    print("Function Calling and MCP are fully at parity for this run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
