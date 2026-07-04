"""Shared, architecture-independent agent configuration.

Both the `function_calling` and `mcp` modes of the orchestrator MUST use
these exact constants, so that model/temperature/system prompt are never a
confound when comparing the two architectures.
"""

MODEL = "claude-sonnet-4-6"
TEMPERATURE = 0.0
MAX_TOKENS = 1024

SYSTEM_PROMPT = (
    "You are an operations assistant for an e-commerce platform built on three "
    "microservices: Catalog (products), Customer, and Order. Use the tools "
    "available to you to answer the user's request. Always use a tool to look "
    "up or create data instead of guessing; never invent ids, prices, or other "
    "field values. If a tool call returns an error, report the error back to "
    "the user in plain language instead of retrying blindly."
)

# Safety bound: an experiment run must never spin forever if the model keeps
# requesting tools in a loop.
MAX_TOOL_ITERATIONS = 8
