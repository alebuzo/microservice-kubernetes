# METODOLOGÍA

## Enfoque de la investigación

La investigación adopta un enfoque mixto (cuantitativo-cualitativo): en primer lugar se ejecutan las pruebas cuantitativas (latencia, volumen de código, número de llamadas) bajo condiciones controladas, y posteriormente se realiza el análisis cualitativo del acoplamiento y la adaptabilidad mediante la observación de los cambios requeridos en cada arquitectura tras la modificación de esquemas en la API y del desarrollo del Function Calling y el servidor MCP.

## Diseño de investigación

Dos grupos de tratamiento: Function Calling (REST API) y Model Context Protocol (MCP, desplegado localmente), sometidos a las mismas condiciones de prueba (mismo modelo de lenguaje, mismos escenarios, mismos cambios de esquema), de modo que la arquitectura de integración sea la única variable independiente relevante.

## Objeto de estudio

Se utilizará el repositorio open source **microservice-kubernetes** (ewolff, [https://github.com/ewolff/microservice-kubernetes](https://github.com/ewolff/microservice-kubernetes)), desplegado localmente en Kubernetes. Este proyecto implementa un sistema de microservicios en Java (Spring/Spring Cloud) que se comunican entre sí mediante REST, compuesto por tres servicios:

**Tabla 1. Servicios del proyecto en estudio**

| Microservicio | Función | Rol en el experimento |
|---|---|---|
| Catalog | Gestión de ítems del catálogo | Escenario de baja complejidad |
| Customer | Gestión de datos de clientes | Escenario de complejidad media |
| Order | Procesamiento de pedidos (orquesta a Catalog y Customer) | Escenario de alta complejidad (flujo multi-servicio) |

Se seleccionará un subconjunto representativo de endpoints de estos tres microservicios, suficiente para ejecutar los tres escenarios de prueba definidos, documentando el contrato original (request/response) de cada endpoint seleccionado como línea base antes de cualquier modificación.

## Desarrollo de las integraciones (Function Calling y MCP)

Dado que el repositorio base no incluye integraciones con LLMs, ambas arquitecturas serán desarrolladas manualmente sobre los endpoints REST seleccionados:

**a) Function Calling (REST API):** definición manual de las funciones (esquemas JSON) correspondientes a los endpoints seleccionados, incluyendo nombre, descripción semántica, esquema de parámetros y la lógica de invocación HTTP hacia el microservicio correspondiente.

**b) Servidor MCP (local):** implementación de un servidor MCP local, siguiendo la especificación oficial del protocolo, que expone las mismas operaciones como tools (nombre, descripción, input schema), con la lógica de ejecución que traduce cada invocación en una llamada REST al microservicio correspondiente, sobre un transporte local (stdio o HTTP local).

**c) Paridad funcional:** ambas arquitecturas expondrán el mismo conjunto de operaciones, con la misma semántica y los mismos parámetros de entrada/salida antes de aplicar los cambios de esquema, garantizando que las diferencias observadas sean atribuibles a la arquitectura y no a una implementación desigual.

## Modelo de lenguaje

Se utilizará un único modelo de lenguaje en la totalidad del experimento: **Claude Sonnet 4.6 (Anthropic)**:

- Elimina la variabilidad asociada a diferencias de razonamiento o comportamiento entre modelos distintos, que introduciría una variable de confusión.
- Anthropic es el creador del protocolo MCP, por lo que Claude Sonnet 4.6 ofrece soporte nativo y estable tanto para function calling como para MCP.
- Mantiene constantes los parámetros del modelo (temperatura, system prompt, ventana de contexto) entre ambas condiciones experimentales.

## Escenarios de prueba

Se diseñan tres escenarios de complejidad creciente, alineados con la estructura de orquestación nativa del sistema base:

- **Bajo (Catalog):** consulta de un ítem del catálogo. Una sola llamada REST, sin dependencias entre servicios.
- **Medio (Customer):** consulta o creación de un cliente. Una sola llamada, con una estructura de datos algo más rica (datos personales, dirección).
- **Alto (Order):** creación de un pedido. Flujo multi-servicio, ya que Order invoca internamente a Catalog (validación de ítems) y a Customer (validación del cliente), generando llamadas encadenadas.

## Variable: cambios de esquema

Para el objetivo específico 1 (acoplamiento y adaptabilidad), se aplicará una combinación de cambios controlados sobre la API de cada microservicio, uno a la vez:

- Renombrar campos/parámetros (ej. `itemId` → `id_item`)
- Cambiar la estructura de datos (flat → nested, ej. mover `price` a un objeto `{amount, currency}`)
- Agregar parámetros obligatorios nuevos (ej. requerir `paymentMethod` en la creación de un pedido)

Cada cambio se aplicará a un microservicio a la vez, registrando cuántas modificaciones son necesarias en cada arquitectura (definición de función/tool, lógica de invocación, código del agente) para restaurar el funcionamiento correcto. El esquema original se restaurará entre cada prueba para mantener el control experimental.

## Variables e indicadores

**Tabla 2. Variables e indicadores para cada objetivo específico**

| Objetivo específico | Variable | Indicador | Naturaleza de la medición |
|---|---|---|---|
| OE1 (cualitativo) | Acoplamiento | N.° de archivos/líneas modificadas tras el cambio de esquema | Por cada cambio de esquema aplicado |
| OE1 (cualitativo) | Adaptabilidad | Tiempo/esfuerzo para restaurar funcionalidad | Por cada cambio de esquema aplicado |
| OE2 (cuantitativo) | Latencia end-to-end | Milisegundos desde la solicitud del usuario hasta la respuesta final | Por ejecución (n=5 por escenario y arquitectura) |
| OE2 (cuantitativo) | N.° de llamadas del agente | Conteo de invocaciones a herramientas por tarea | Por ejecución (n=5 por escenario y arquitectura) |
| OE2 (cuantitativo) | Volumen de código de integración | LOC de: (a) definición de funciones/tools, (b) lógica de invocación al microservicio, (c) código de orquestación del agente (loop de tool-use, manejo de sesión, despacho de llamadas, manejo de errores) | Medida fija, registrada una sola vez por arquitectura tras finalizar la implementación (no varía por ejecución) |

## Instrumentos y herramientas

**Tabla 3. Herramientas de medición**

| Componente | Herramienta / Especificación |
|---|---|
| Orquestación de infraestructura | Kubernetes local (minikube/kind/Docker Desktop) |
| Definición de funciones (Function Calling) | Python, esquema JSON de la API de Anthropic |
| Servidor MCP | Python (SDK oficial de MCP) o TypeScript |
| Cliente del agente (orquestador) | Python, consumiendo ambas integraciones de forma intercambiable |
| LLM | Claude Sonnet 4.6 (Anthropic), vía API (`claude-sonnet-4-6`) |
| Medición de latencia y llamadas | requests/httpx + logging custom (timestamps, contadores), exportado a CSV/JSON |
| Medición de volumen de código | cloc |
| Análisis de datos | pandas (estadística descriptiva: media, mediana, desviación estándar, mínimo/máximo) |
| Control de versiones / diffs | Git, para rastrear modificaciones por cada cambio de esquema |
| Repeticiones | n = 5 por escenario y arquitectura (5 con Function Calling + 5 con MCP), totalizando 30 ejecuciones cuantitativas |

## Procedimiento

1. Clonar y desplegar localmente el sistema de microservicios en Kubernetes.
2. Verificar el funcionamiento base de los tres microservicios vía REST.
3. Seleccionar el subconjunto de endpoints de Catalog, Customer y Order necesarios para los tres escenarios, y documentar su contrato original (línea base).
4. Desarrollar manualmente las funciones de Function Calling para los endpoints seleccionados, verificando su correcta invocación.
5. Desarrollar manualmente el servidor MCP local con las herramientas equivalentes, verificando la conexión cliente-servidor.
6. Medir el volumen de código (LOC) de cada arquitectura con cloc, una sola vez, al finalizar la implementación.
7. Ejecutar las pruebas cuantitativas: 5 repeticiones con Function Calling + 5 con MCP, por cada uno de los tres escenarios, registrando latencia y n.° de llamadas del agente.
8. Aplicar cada cambio de esquema (uno a la vez) sobre el microservicio correspondiente, registrando las modificaciones necesarias en cada arquitectura para restaurar la funcionalidad; restaurar el esquema original entre cada prueba.
9. Procesar y analizar estadísticamente los datos cuantitativos (medidas descriptivas).
10. Analizar cualitativamente el acoplamiento y la adaptabilidad observados por cada cambio aplicado.
11. Construir la matriz comparativa final, presentando los resultados de cada criterio por separado, sin ponderación.