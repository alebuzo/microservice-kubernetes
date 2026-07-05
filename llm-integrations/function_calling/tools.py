"""Anthropic tool-use schemas for the Function Calling architecture.

Each entry follows the `tools` parameter shape expected by
`anthropic.Anthropic().messages.create(tools=[...])`: a dict with
`name`, `description` and a JSON Schema `input_schema`.

One tool per scenario operation, matching `experiments/baseline_contracts.md`:
  - Bajo:  get_catalog_item
  - Medio: get_customer, create_customer
  - Alto:  create_order, get_order
"""

TOOL_DEFINITIONS: list[dict] = [
    {
        "name": "get_catalog_item",
        "description": (
            "Fetch a single product from the Catalog service by its numeric id. "
            "Returns id, name and price, or an error if the item does not exist."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "integer",
                    "description": "The catalog item id to look up.",
                },
            },
            "required": ["item_id"],
        },
    },
    {
        "name": "get_customer",
        "description": (
            "Fetch a single customer from the Customer service by its numeric id. "
            "Returns id, name, firstname, email, street and city, or an error if the "
            "customer does not exist."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "integer",
                    "description": "The customer id to look up.",
                },
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "create_customer",
        "description": "Create a new customer in the Customer service.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Customer's last name."},
                "firstname": {"type": "string", "description": "Customer's first name."},
                "email": {"type": "string", "description": "Customer's email address."},
                "street": {"type": "string", "description": "Street address."},
                "city": {"type": "string", "description": "City."},
            },
            "required": ["name", "firstname", "email", "street", "city"],
        },
    },
    {
        "name": "create_order",
        "description": (
            "Create a new order in the Order service for a given customer and a list "
            "of order lines (item id + quantity). The Order service validates that the "
            "customer and every item id actually exist (calling Customer and Catalog "
            "internally) before accepting the order; if any id is invalid it returns an "
            "error instead of creating the order. A payment method is required; if the "
            "user doesn't mention one, ask them for it before calling this tool."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "integer",
                    "description": "Id of the customer placing the order.",
                },
                "order_lines": {
                    "type": "array",
                    "description": "List of order lines.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item_id": {"type": "integer", "description": "Catalog item id."},
                            "count": {"type": "integer", "description": "Quantity ordered."},
                        },
                        "required": ["item_id", "count"],
                    },
                },
                "payment_method": {
                    "type": "string",
                    "description": (
                        "How the customer wants to pay (e.g. 'card', 'paypal', 'cash'). "
                        "Free-form text; required by the Order service."
                    ),
                },
            },
            "required": ["customer_id", "order_lines", "payment_method"],
        },
    },
    {
        "name": "get_order",
        "description": "Fetch a single order from the Order service by its numeric id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "integer",
                    "description": "The order id to look up.",
                },
            },
            "required": ["order_id"],
        },
    },
]
