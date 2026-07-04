# Scripts de prueba — resumen por tipo

Todos los comandos se ejecutan desde `llm-integrations/` con el entorno virtual
activo (`source .venv/bin/activate`) y los `kubectl port-forward` de
catalog/customer/order levantados (18081/18082/18083), salvo que se indique
lo contrario.

## 1. Verificación de entorno/acceso

- `orchestrator/verify_api_access.py` — Confirma que la API de Anthropic es alcanzable y responde, sin tocar los microservicios.

## 2. Pruebas manuales por arquitectura (smoke test, sin LLM)

- `function_calling/manual_test.py` — Ejercita los 5 tools de Function Calling directo por HTTP (sin modelo) contra el clúster real.
- `mcp_server/manual_test.py` — Igual que el anterior pero contra el servidor MCP real (vía stdio), mismos casos de prueba.

## 3. Prueba de paridad funcional entre arquitecturas (sin LLM)

- `scenarios/parity_check.py` — Corre los mismos casos contra Function Calling y MCP y compara resultados/esquemas para detectar divergencias entre ambas arquitecturas.

## 4. Pruebas end-to-end con LLM real (escenarios experimentales)

- `orchestrator/agent.py` — Ejecuta una corrida individual del agente (Bajo/Medio/Alto/manual) en el modo elegido (`--mode function_calling|mcp`), con instrumentación de latencia/tool calls.
- `scenarios/run_scenario.py` — Repite un escenario N veces contra una arquitectura y variante de esquema, registrando cada corrida.
- `run_all_scenarios.sh` — Dispara las 30 corridas completas (3 escenarios × 2 arquitecturas × 5 repeticiones) para una variante de esquema dada.

## 5. Medición de código (LOC)

- `loc_measurement.sh` — Calcula líneas de código por arquitectura (Function Calling vs MCP, más módulos compartidos) con `cloc`.

## 6. Herramientas de cambio de esquema (no son pruebas, preparan el terreno para ellas)

- `schema_changes/apply.sh` — Aplica una de las 3 variantes de cambio de esquema al Deployment real en K8s.
- `schema_changes/revert.sh` — Revierte una variante de cambio de esquema al baseline correcto de cada servicio.
