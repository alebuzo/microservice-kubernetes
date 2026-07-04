"""Manual smoke test for the Function Calling tool dispatch, independent of
the Anthropic API (no LLM calls) — just exercises the HTTP wiring against a
real running cluster, the same way `verify_api_access.py` does for the
Anthropic API.

Run from `llm-integrations/` with the same port-forwards used throughout
this project active:
    kubectl port-forward svc/catalog  18081:8080
    kubectl port-forward svc/customer 18082:8080
    kubectl port-forward svc/order    18083:8080

Usage:
    cd llm-integrations
    source .venv/bin/activate
    python -m function_calling.manual_test
"""

import json

from function_calling.client import call_tool

CASES: list[tuple[str, dict]] = [
    ("get_catalog_item", {"item_id": 1}),
    ("get_catalog_item", {"item_id": 9999}),  # expected error
    ("get_customer", {"customer_id": 1}),
    ("get_customer", {"customer_id": 9999}),  # expected error
    ("create_order", {"customer_id": 1, "order_lines": [{"item_id": 1, "count": 1}]}),
    ("create_order", {"customer_id": 1, "order_lines": [{"item_id": 9999, "count": 1}]}),  # expected error
]


def main() -> int:
    failures = 0
    for name, args in CASES:
        result = call_tool(name, args)
        ok = "error" not in result or "9999" in json.dumps(args)
        status = "OK" if ok else "UNEXPECTED"
        print(f"[{status}] {name}({args}) -> {result}")
        if not ok:
            failures += 1
    if failures:
        print(f"\n{failures} unexpected result(s).")
        return 1
    print("\nAll function_calling tool calls behaved as expected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
