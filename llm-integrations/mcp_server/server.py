"""Local MCP server for the Function Calling vs MCP experiment.

Exposes the same 5 operations as `llm-integrations/function_calling/tools.py`
(same names, same parameter semantics), so the shared orchestrator gets
functional parity between architectures. Delegates all actual HTTP work to
`llm-integrations/common/services.py` — the only code that is specific to
MCP here is the tool registration/wiring below (transport: stdio).

Run standalone (e.g. to validate startup):
    cd llm-integrations
    source .venv/bin/activate
    python -m mcp_server.server
"""

from mcp.server.fastmcp import FastMCP

from common.services import (
    ServiceCallError,
    create_customer as _create_customer,
    create_order as _create_order,
    get_catalog_item as _get_catalog_item,
    get_customer as _get_customer,
    get_order as _get_order,
)

mcp = FastMCP("microservice-kubernetes-tools")


@mcp.tool()
def get_catalog_item(item_id: int) -> dict:
    """Fetch a single product from the Catalog service by its numeric id.

    Returns id, name and price, or an error if the item does not exist.
    """
    try:
        return _get_catalog_item(item_id)
    except ServiceCallError as exc:
        return {"error": str(exc), "status_code": exc.status_code}


@mcp.tool()
def get_customer(customer_id: int) -> dict:
    """Fetch a single customer from the Customer service by its numeric id.

    Returns id, name, firstname, email, street and city, or an error if the
    customer does not exist.
    """
    try:
        return _get_customer(customer_id)
    except ServiceCallError as exc:
        return {"error": str(exc), "status_code": exc.status_code}


@mcp.tool()
def create_customer(name: str, firstname: str, email: str, street: str, city: str) -> dict:
    """Create a new customer in the Customer service."""
    try:
        return _create_customer(
            name=name, firstname=firstname, email=email, street=street, city=city
        )
    except ServiceCallError as exc:
        return {"error": str(exc), "status_code": exc.status_code}


@mcp.tool()
def create_order(customer_id: int, order_lines: list[dict], payment_method: str) -> dict:
    """Create a new order in the Order service for a given customer and a
    list of order lines (each `{"item_id": <int>, "count": <int>}`).

    The Order service validates that the customer and every item id
    actually exist (calling Customer and Catalog internally) before
    accepting the order; if any id is invalid it returns an error instead
    of creating the order.

    `payment_method` is required (e.g. "card", "paypal", "cash" -
    free-form text). If the user doesn't mention one, ask them for it
    before calling this tool.
    """
    try:
        lines = [{"itemId": line["item_id"], "count": line["count"]} for line in order_lines]
        return _create_order(customer_id=customer_id, order_lines=lines, payment_method=payment_method)
    except ServiceCallError as exc:
        return {"error": str(exc), "status_code": exc.status_code}
    except KeyError as exc:
        return {"error": f"Missing required field {exc} in an order line"}


@mcp.tool()
def get_order(order_id: int) -> dict:
    """Fetch a single order from the Order service by its numeric id."""
    try:
        return _get_order(order_id)
    except ServiceCallError as exc:
        return {"error": str(exc), "status_code": exc.status_code}


if __name__ == "__main__":
    mcp.run(transport="stdio")
