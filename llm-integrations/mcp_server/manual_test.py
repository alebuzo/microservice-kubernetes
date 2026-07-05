"""Manual smoke test for the MCP server, independent of the Anthropic API
(no LLM calls) — spawns `mcp_server/server.py` as a stdio subprocess, lists
its tools, and calls each of them the same way `function_calling/manual_test.py`
does for the Function Calling architecture (same cases, same expected
outcomes), against a real running cluster.

Run from `llm-integrations/` with the same port-forwards used throughout
this project active:
    kubectl port-forward svc/catalog  18081:8080
    kubectl port-forward svc/customer 18082:8080
    kubectl port-forward svc/order    18083:8080

Usage:
    cd llm-integrations
    source .venv/bin/activate
    python -m mcp_server.manual_test
"""

import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

CASES: list[tuple[str, dict]] = [
    ("get_catalog_item", {"item_id": 1}),
    ("get_catalog_item", {"item_id": 9999}),  # expected error
    ("get_customer", {"customer_id": 1}),
    ("get_customer", {"customer_id": 9999}),  # expected error
    ("create_order", {"customer_id": 1, "order_lines": [{"item_id": 1, "count": 1}], "payment_method": "card"}),
    ("create_order", {"customer_id": 1, "order_lines": [{"item_id": 9999, "count": 1}], "payment_method": "card"}),  # expected error
]


async def main() -> int:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server.server"],
    )

    failures = 0
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            tool_names = sorted(t.name for t in tools.tools)
            print(f"Discovered tools: {tool_names}\n")

            for name, args in CASES:
                result = await session.call_tool(name, args)
                text = "".join(
                    block.text for block in result.content if block.type == "text"
                )
                try:
                    parsed = json.loads(text)
                except ValueError:
                    parsed = text
                is_error_case = "9999" in json.dumps(args)
                has_error = isinstance(parsed, dict) and "error" in parsed
                ok = has_error == is_error_case
                status = "OK" if ok else "UNEXPECTED"
                print(f"[{status}] {name}({args}) -> {parsed}")
                if not ok:
                    failures += 1

    if failures:
        print(f"\n{failures} unexpected result(s).")
        return 1
    print("\nAll MCP tool calls behaved as expected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
