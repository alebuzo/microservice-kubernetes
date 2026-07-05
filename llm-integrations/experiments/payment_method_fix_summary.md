# Fix: schema-change #3 (`payment-method`) — MCP

## Contexto

Tras aplicar `payment-method` (Order ahora exige un campo `paymentMethod`
no vacío en `POST /orders`, ver `schema_changes/03-payment-method.patch`),
el agente vía **MCP** era incapaz de crear una orden: el tool `create_order`
no exponía ningún parámetro de método de pago, así que el LLM nunca podía
enviarlo, y el request al Order service fallaba con HTTP 400
(`paymentMethod is required`).

## Cambios realizados

| Archivo | Cambio |
|---|---|
| `common/services.py` | `create_order()` gana un parámetro obligatorio `payment_method: str`, agregado al payload como `paymentMethod`. (Idéntico al fix del branch `fix-payment-method-fc`, ya que este módulo es compartido entre ambas arquitecturas.) |
| `mcp_server/server.py` | La función-tool `create_order` (decorada con `@mcp.tool()`) gana el parámetro `payment_method: str`, documentado en su docstring (FastMCP genera el schema del tool a partir de la firma + docstring, no de un JSON Schema manual como en Function Calling), y lo reenvía a `_create_order`. |
| `mcp_server/manual_test.py` | Los dos ejemplos de `create_order` se actualizan para incluir `payment_method` (no cuenta para la métrica de acoplamiento — son datos de prueba, no lógica). |

## Líneas de código necesarias (acoplamiento)

Medido con `git diff --stat` sobre los archivos de lógica (excluyendo `manual_test.py`):

```
llm-integrations/common/services.py   | 13 +++++++++++--
llm-integrations/mcp_server/server.py |  8 ++++++--
2 files changed, 17 insertions(+), 4 deletions(-)
```

- **Archivos modificados**: 2
- **Líneas netas añadidas**: 17 (+) / 4 (−)

Nota comparativa: MCP necesitó **menos líneas** que Function Calling (17
vs 22) y **un archivo menos** (2 vs 3), porque FastMCP deriva el schema del
tool automáticamente de la firma de la función Python (no hay un
`input_schema` JSON manual que mantener aparte, como en
`function_calling/tools.py`).

## Verificación

Probado en vivo contra el clúster con `payment-method` aplicado
(`ORDER_BASE_URL=http://localhost:18083`), vía la capa de servicios
compartida (equivalente a lo que invoca el tool MCP):

```python
create_order(customer_id=1, order_lines=[{"itemId": 1, "count": 1}], payment_method="paypal")
# -> {'id': 6, 'customerId': 1, 'orderLine': [{'itemId': 1, 'count': 1}]}
```

Antes del fix, la misma llamada (sin `payment_method`) producía un
HTTP 400 desde el Order service.
