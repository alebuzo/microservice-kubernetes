"""Fixed user prompts for the 3 methodology scenarios (Bajo/Medio/Alto).

Keeping these as constants (rather than letting scenario-runner callers
improvise wording) is what makes the 5 repetitions per (scenario, mode,
schema_variant) combination comparable: the only thing that varies between
runs of the same scenario is the architecture (Function Calling vs MCP) and,
later, the schema variant under test — never the prompt itself.

- Bajo  (Catalog):  single read-only lookup -> 1 expected tool call.
- Medio (Customer): create + verify        -> 2 expected tool calls.
- Alto  (Order):    order creation that triggers the Order service's
                     internal Catalog+Customer validation chain (see
                     `order-item-validation-fix` in plan.md) -> 1 tool call
                     from the agent's perspective, but a multi-service call
                     chain inside the Order microservice itself.
"""

SCENARIO_PROMPTS: dict[str, str] = {
    "bajo": "What is the price of catalog item 1?",
    "medio": (
        "Create a new customer named Ada Lovelace (email ada@example.com, "
        "street 12 Analytical Engine Row, city London), then look them up "
        "again by the id you got back and confirm their details."
    ),
    "alto": (
        "Place a new order for customer 1 with 2 units of catalog item 1, "
        "then report the order id you got back."
    ),
}

EXPECTED_TOOL_CALLS: dict[str, int] = {
    "bajo": 1,
    "medio": 2,
    "alto": 1,
}
