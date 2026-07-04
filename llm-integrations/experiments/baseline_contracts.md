# Baseline API Contracts (pre-schema-change)

Documented by deploying the existing public Docker images (`ewolff/microservice-kubernetes-demo-*`)
to a local Kubernetes cluster (`kubectl apply -f microservices.yaml`) and querying each service
directly via `kubectl port-forward` (bypassing the Apache HTML reverse proxy, which only serves
`*.html` views, not JSON).

Verified: `kubectl get nodes` → 1-node cluster (`desktop-control-plane`, Docker Desktop K8s),
all 4 pods (`apache`, `catalog`, `customer`, `order`) `Running`.

Port-forwards used for baseline verification:
```
kubectl port-forward svc/catalog  18081:8080
kubectl port-forward svc/customer 18082:8080
kubectl port-forward svc/order    18083:8080
```

## ⚠️ Important finding: Order's Spring Data REST JSON API is broken/shadowed

Catalog and Customer expose a working Spring Data REST JSON API at `/catalog` and `/customer`
respectively (see below), because their HTML controllers (`CatalogController`, `CustomerController`)
map paths with an explicit `.html` suffix (e.g. `/{id}.html`), which does not collide with the
Spring Data REST paths (`/catalog/{id}`, `/customer/{id}`).

**Order is different.** `OrderController` (HTML) maps directly to bare paths: `/` (GET/POST),
`/{id}` (GET/DELETE), `/form.html`, `/line`. These collide directly with the Spring Data REST
endpoints that `@RepositoryRestResource(path = "order")` would otherwise expose at `/order` and
`/order/{id}`.

Observed behavior (confirmed by curl + pod logs):
- `GET /order` → HTTP 400. Spring MVC routes it to `OrderController.get(@PathVariable("id") long id)`
  (the bare `/{id}` mapping), tries to parse the literal string `"order"` as a `long`, and throws
  `MethodArgumentTypeMismatchException` / `NumberFormatException`.
- `GET /1` → HTTP 500 (Internal Server Error) — reaches `OrderController.get(1)`, not Spring Data REST.
- `GET /profile` → HTTP 400 (Spring Data REST's profile endpoint is also shadowed).

**Consequence:** there is no usable existing JSON endpoint for creating or reading Orders as
structured data. This directly motivates plan task `order-json-endpoint`: a brand-new
`@RestController` must be added on a path that does **not** collide with the existing HTML
`OrderController` mappings (e.g. `/orders` or `/api/orders`, plural, distinct from the HTML
controller's bare `/`, `/{id}`). This will also be the endpoint used by both the Function Calling
and MCP tools for the "Alto" scenario.

## Catalog (Bajo scenario) — `GET /catalog/{id}`

Base URL (via port-forward): `http://localhost:18081`

**Request:**
```
GET /catalog/1
Accept: application/json
```

**Response (HTTP 200, HAL+JSON):**
```json
{
  "id": 1,
  "name": "iPod",
  "price": 42.0,
  "_links": {
    "self": { "href": "http://localhost:18081/catalog/1" },
    "item": { "href": "http://localhost:18081/catalog/1" }
  }
}
```

**Collection:** `GET /catalog` → HAL-wrapped page (`_embedded.catalog[]`, `page.{size,totalElements,totalPages,number}`).

**Search:** `GET /catalog/search/findByNameContaining?name={query}` → same item shape, HAL-wrapped collection.

**Fields:** `id` (long), `name` (string), `price` (double, flat — target of schema-change #2: nest into `{amount, currency}`). Note: the client-facing field is `itemId` in `com.ewolff.microservice.order.clients.Item` (Order's client-side DTO) but `id` in the Catalog microservice's own domain model / JSON — this naming difference is itself relevant context for schema-change #1 (`itemId` → `id_item`).

## Customer (Medio scenario) — `GET/POST /customer`

Base URL: `http://localhost:18082`

**Request:**
```
GET /customer/1
Accept: application/json
```

**Response (HTTP 200, HAL+JSON):**
```json
{
  "id": 1,
  "name": "Wolff",
  "firstname": "Eberhard",
  "email": "eberhard.wolff@gmail.com",
  "street": "Unter den Linden",
  "city": "Berlin",
  "_links": {
    "self": { "href": "http://localhost:18082/customer/1" },
    "customer": { "href": "http://localhost:18082/customer/1" }
  }
}
```

**Create:** `POST /customer` with JSON body `{"name","firstname","email","street","city"}` (no `id`) → HTTP 201 with `Location` header.

**Fields:** `id` (long), `name`, `firstname`, `email`, `street`, `city` (all string). No nested structure today (relevant if a schema change targets flat→nested here, though the plan's 3 defined changes target Catalog and Order specifically).

## Order (Alto scenario) — to be exposed via NEW endpoint (see `order-json-endpoint` task)

Current domain model (`com.ewolff.microservice.order.logic.Order`):
```json
{
  "id": 0,
  "customerId": 1,
  "orderLine": [
    { "count": 2, "itemId": 1 }
  ]
}
```

Current server-side validation (`OrderService.order()`, only reachable via the HTML form POST today):
- Rejects orders with zero lines (`IllegalArgumentException`).
- Validates `customerId` via `CustomerClient.isValidCustomerId()`.
- Does **NOT** validate that `itemId`s exist in Catalog (gap — to be fixed by `order-item-validation-fix`).
- Does **NOT** require a `paymentMethod` field (target of schema-change #3, to be added later).

Planned new endpoint (task `order-json-endpoint`): `POST /orders` (JSON) → invokes
`OrderService.order()` (with the added item validation) → returns created order as JSON or a
validation error (400) if customer or any item id is invalid.

## Schema-change targets (OE1, for later `schema-change-tooling` task)

1. Catalog: rename `itemId` → `id_item` (naming inconsistency: client DTO already uses `itemId`, domain model uses `id` — needs clarification of which representation is the "public contract" being renamed).
2. Catalog: nest `price` (flat double) → `price: { amount, currency }`.
3. Order: add new required `paymentMethod` field to order creation (depends on `order-json-endpoint` existing first).
