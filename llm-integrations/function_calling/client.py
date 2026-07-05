"""Dispatch layer: maps a tool name + arguments (as sent by the model in a
`tool_use` content block) to the corresponding REST call in
`llm-integrations/common/services.py`, and shapes the result back into a
plain dict suitable for a `tool_result` content block.

On a downstream HTTP error, `call_tool` does NOT raise: it returns a dict
with an `"error"` key so the orchestrator can feed it back to the model as
the tool result (mirroring how the deployed `/orders` endpoint itself
reports validation errors as JSON, not as transport failures).
"""

from typing import Any

from common.services import (
    ServiceCallError,
    create_customer,
    create_order,
    get_catalog_item,
    get_customer,
    get_order,
)

TOOL_FUNCTIONS = {
    "get_catalog_item": lambda args: get_catalog_item(args["item_id"]),
    "get_customer": lambda args: get_customer(args["customer_id"]),
    "create_customer": lambda args: create_customer(
        name=args["name"],
        firstname=args["firstname"],
        email=args["email"],
        street=args["street"],
        city=args["city"],
    ),
    "create_order": lambda args: create_order(
        customer_id=args["customer_id"],
        order_lines=[
            {"itemId": line["item_id"], "count": line["count"]}
            for line in args["order_lines"]
        ],
        payment_method=args["payment_method"],
    ),
    "get_order": lambda args: get_order(args["order_id"]),
}


def call_tool(name: str, arguments: dict) -> dict[str, Any]:
    """Invoke the tool named `name` with `arguments` and return its result.

    Returns `{"error": "..."}` (never raises) if the tool name is unknown,
    the arguments are malformed, or the downstream service call fails.
    """
    handler = TOOL_FUNCTIONS.get(name)
    if handler is None:
        return {"error": f"Unknown tool: {name}"}

    try:
        return handler(arguments)
    except ServiceCallError as exc:
        return {"error": str(exc), "status_code": exc.status_code}
    except KeyError as exc:
        return {"error": f"Missing required argument {exc} for tool {name}"}
