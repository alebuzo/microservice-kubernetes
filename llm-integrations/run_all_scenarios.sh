#!/usr/bin/env bash
# Runs the full baseline experiment: 3 scenarios x 2 architectures x 5 reps
# = 30 runs, all logged to experiments/results/runs.csv (schema_variant
# defaults to "baseline" — for the 3 schema-change variants, use
# `schema-change-tooling`'s scripts together with `--schema-variant`, e.g.:
#   ./run_all_scenarios.sh itemid-rename
#
# Prerequisites (same as every manual test in this project):
#   - kubectl port-forward svc/catalog  18081:8080
#   - kubectl port-forward svc/customer 18082:8080
#   - kubectl port-forward svc/order    18083:8080
#   - ANTHROPIC_API_KEY exported in this shell
#
# Usage (from llm-integrations/):
#   source .venv/bin/activate
#   ./run_all_scenarios.sh [schema_variant] [reps]
#
# schema_variant defaults to "baseline"; reps defaults to 5.

set -euo pipefail

SCHEMA_VARIANT="${1:-baseline}"
REPS="${2:-5}"

SCENARIOS=(bajo medio alto)
MODES=(function_calling mcp)

for scenario in "${SCENARIOS[@]}"; do
  for mode in "${MODES[@]}"; do
    python -m scenarios.run_scenario \
      --scenario "$scenario" \
      --mode "$mode" \
      --reps "$REPS" \
      --schema-variant "$SCHEMA_VARIANT"
  done
done

echo
echo "Done. $(( ${#SCENARIOS[@]} * ${#MODES[@]} * REPS )) runs logged to experiments/results/runs.csv"
echo "(schema_variant=$SCHEMA_VARIANT)"
