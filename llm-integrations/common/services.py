"""Shared REST invocation logic for the Catalog, Customer and Order services.

Both the Function Calling integration (`llm-integrations/function_calling/`)
and the MCP server (`llm-integrations/mcp_server/`) call into this module so
that the underlying HTTP behaviour (base URLs, timeouts, error shaping) is
identical between architectures. This keeps the functional-parity guarantee
required by the experiment while leaving each architecture's own
tool-definition/wiring code (the thing whose LOC actually gets compared) in
its own package.

Base URLs default to the `kubectl port-forward` ports used throughout this
project's manual verification (see `experiments/baseline_contracts.md`):
    kubectl port-forward svc/catalog  18081:8080
    kubectl port-forward svc/customer 18082:8080
    kubectl port-forward svc/order    18083:8080
They can be overridden with the CATALOG_BASE_URL / CUSTOMER_BASE_URL /
ORDER_BASE_URL environment variables (e.g. to point at in-cluster DNS names
when running the orchestrator from inside the cluster).
"""

import os
from typing import Any

import httpx

CATALOG_BASE_URL = os.environ.get("CATALOG_BASE_URL", "http://localhost:18081")
CUSTOMER_BASE_URL = os.environ.get("CUSTOMER_BASE_URL", "http://localhost:18082")
ORDER_BASE_URL = os.environ.get("ORDER_BASE_URL", "http://localhost:18083")

DEFAULT_TIMEOUT_SECONDS = 10.0


class ServiceCallError(Exception):
    """Raised when a downstream microservice call fails.

    Carries enough structured detail (`status_code`, `detail`) for the
    calling architecture (Function Calling or MCP) to report a tool error
    back to the model instead of crashing the orchestrator.
    """

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.detail = message


def _request(method: str, url: str, **kwargs: Any) -> dict:
    try:
        response = httpx.request(method, url, timeout=DEFAULT_TIMEOUT_SECONDS, **kwargs)
    except httpx.RequestError as exc:
        raise ServiceCallError(f"network error calling {method} {url}: {exc}") from exc

    if response.status_code >= 400:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise ServiceCallError(
            f"{method} {url} failed with HTTP {response.status_code}: {detail}",
            status_code=response.status_code,
        )

    if not response.content:
        return {}
    return response.json()


def get_catalog_item(item_id: int) -> dict:
    """Bajo scenario: fetch a single catalog item by id (`GET /catalog/{id}`)."""
    return _request("GET", f"{CATALOG_BASE_URL}/catalog/{item_id}")


def get_customer(customer_id: int) -> dict:
    """Medio scenario: fetch a single customer by id (`GET /customer/{id}`)."""
    return _request("GET", f"{CUSTOMER_BASE_URL}/customer/{customer_id}")


def create_customer(name: str, firstname: str, email: str, street: str, city: str) -> dict:
    """Medio scenario: create a new customer (`POST /customer`)."""
    payload = {
        "name": name,
        "firstname": firstname,
        "email": email,
        "street": street,
        "city": city,
    }
    return _request("POST", f"{CUSTOMER_BASE_URL}/customer", json=payload)


def create_order(customer_id: int, order_lines: list[dict]) -> dict:
    """Alto scenario: create a new order (`POST /orders`).

    `order_lines` items look like `{"itemId": <int>, "count": <int>}`.
    Order service validates both `customer_id` and every `itemId` against
    Customer/Catalog before accepting the order (see `order-item-validation-fix`).
    """
    payload = {"customerId": customer_id, "orderLine": order_lines}
    return _request("POST", f"{ORDER_BASE_URL}/orders", json=payload)


def get_order(order_id: int) -> dict:
    """Alto scenario: fetch a single order by id (`GET /orders/{id}`)."""
    return _request("GET", f"{ORDER_BASE_URL}/orders/{order_id}")
