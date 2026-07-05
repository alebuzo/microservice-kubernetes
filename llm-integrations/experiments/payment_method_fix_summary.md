# Fix: schema-change #3 (`payment-method`) — Function Calling

## Contexto

Tras aplicar `payment-method` (Order ahora exige un campo `paymentMethod`
no vacío en `POST /orders`, ver `schema_changes/03-payment-method.patch`),
el agente de **Function Calling** era incapaz de crear una orden: el tool
`create_order` no exponía ningún parámetro de método de pago, así que el
LLM nunca podía enviarlo, y el request al Order service fallaba con
HTTP 400 (`paymentMethod is required`).

## Cambios realizados

| Archivo | Cambio |
|---|---|
| `common/services.py` | `create_order()` gana un parámetro obligatorio `payment_method: str`, agregado al payload como `paymentMethod`. |
| `function_calling/tools.py` | El JSON Schema del tool `create_order` gana la propiedad `payment_method` (string libre) y se agrega a `required`; se actualiza la descripción para indicarle al LLM que pregunte al usuario si no lo menciona. |
| `function_calling/client.py` | El dispatcher `call_tool` para `create_order` ahora pasa `payment_method=args["payment_method"]` a la función compartida. |
| `function_calling/manual_test.py` | Los dos ejemplos de `create_order` se actualizan para incluir `payment_method` (no cuenta para la métrica de acoplamiento — son datos de prueba, no lógica). |

## Líneas de código necesarias (acoplamiento)

Medido con `git diff --stat` sobre los archivos de lógica (excluyendo `manual_test.py`):

```
llm-integrations/common/services.py         | 13 +++++++++++--
llm-integrations/function_calling/client.py |  1 +
llm-integrations/function_calling/tools.py  | 12 ++++++++++--
3 files changed, 22 insertions(+), 4 deletions(-)
```

- **Archivos modificados**: 3
- **Líneas netas añadidas**: 22 (+) / 4 (−)

## Verificación

Probado en vivo contra el clúster con `payment-method` aplicado
(`ORDER_BASE_URL=http://localhost:18083`):

```python
call_tool("create_order", {
    "customer_id": 1,
    "order_lines": [{"item_id": 1, "count": 1}],
    "payment_method": "card",
})
# -> {'id': 1, 'customerId': 1, 'orderLine': [{'itemId': 1, 'count': 1}]}
```

Antes del fix, la misma llamada (sin `payment_method`) producía un
HTTP 400 desde el Order service.
