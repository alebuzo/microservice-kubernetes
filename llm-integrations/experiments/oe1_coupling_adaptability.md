# OE1 — Registro de acoplamiento y adaptabilidad por cambio de esquema

Llena una fila por cada combinación (variante de esquema × arquitectura).
Instrucciones completas del ciclo de trabajo en la conversación de la sesión
(`apply.sh` → `parity_check.py` → adaptar código → `parity_check.py` →
`git diff --stat` → revertir).

## Cómo llenar cada columna

- **Inicio / Fin**: marca de tiempo (hh:mm:ss) al empezar y terminar de
  adaptar el código de ESA arquitectura para esa variante.
- **Tiempo (min)**: Fin − Inicio.
- **Archivos modificados**: cuenta de líneas en la salida de
  `git diff --stat` (excluyendo la línea de resumen final).
- **Líneas +/-**: columnas `insertions`/`deletions` de la última línea de
  `git diff --stat` (ej. `2 files changed, 8 insertions(+), 3 deletions(-)`).
- **Notas**: qué archivo(s) tocaste y por qué (ej. "ajustar parseo de
  `price` en `common/services.py`, ahora es un dict anidado").

## itemid-rename (Catalog: `id` → `id_item`)

| Arquitectura     | Inicio | Fin | Tiempo (min) | Archivos modificados | Líneas + | Líneas − | Notas |
|------------------|--------|-----|--------------|-----------------------|----------|----------|-------|
| Function Calling |        |     |              |                       |          |          |       |
| MCP              |        |     |              |                       |          |          |       |

## price-nested (Catalog: `price` flat → `{amount, currency}`)

| Arquitectura     | Inicio | Fin | Tiempo (min) | Archivos modificados | Líneas + | Líneas − | Notas |
|------------------|--------|-----|--------------|-----------------------|----------|----------|-------|
| Function Calling |        |     |              |                       |          |          |       |
| MCP              |        |     |              |                       |          |          |       |

## payment-method (Order: nuevo campo requerido `paymentMethod`)

| Arquitectura     | Inicio | Fin | Tiempo (min) | Archivos modificados | Líneas + | Líneas − | Notas |
|------------------|--------|-----|--------------|-----------------------|----------|----------|-------|
| Function Calling |        |     |              |                       |          |          |       |
| MCP              |        |     |              |                       |          |          |       |

## Resumen final (llenar al terminar las 3 variantes)

| Métrica                                  | Function Calling (promedio) | MCP (promedio) |
|-------------------------------------------|------------------------------|-----------------|
| Tiempo de adaptación (min)                |                              |                 |
| Archivos modificados                      |                              |                 |
| Líneas modificadas (+/-)                  |                              |                 |
