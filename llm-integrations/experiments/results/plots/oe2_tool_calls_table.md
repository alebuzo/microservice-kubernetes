# OE2: Número de llamadas del agente por escenario

Valor **fijo** (desviación estándar = 0 en las n=5 corridas de cada combinación) — no varía entre ejecuciones ni entre Function Calling y MCP para el mismo escenario. Por eso se documenta como tabla y no como gráfico: un gráfico de barras mostraría pares de barras idénticas sin información estadística adicional.

| Escenario | Arquitectura | N.° llamadas al agente (tool calls) | LLM round-trips |
|---|---|---|---|
| Bajo | Function Calling | 1 | 2 |
| Bajo | MCP | 1 | 2 |
| Medio | Function Calling | 2 | 3 |
| Medio | MCP | 2 | 3 |
| Alto | Function Calling | 3 | 3 |
| Alto | MCP | 3 | 3 |
