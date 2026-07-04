#!/usr/bin/env bash
# LOC measurement for the Function Calling vs MCP experiment (task
# `loc-measurement-setup`).
#
# Measures lines of code separately for:
#   - function_calling/  : Function Calling tool definitions + HTTP dispatch
#   - mcp_server/         : MCP tool definitions/registration (delegates HTTP
#                           work to the shared common/ module, so this is
#                           expected to be thinner)
#   - common/             : shared REST invocation logic (used by BOTH
#                           architectures — reported separately, for
#                           transparency, NOT added to either architecture's
#                           total, since it is not a differentiator between
#                           them)
#   - orchestrator/       : shared agent loop + measurement instrumentation
#                           (also common to both architectures, reported
#                           separately for context)
#
# Run this ONCE, after both integrations are finalized (i.e. now, and again
# only if either integration's code changes materially), from the
# `llm-integrations/` directory:
#
#   cd llm-integrations
#   ./loc_measurement.sh
#
# Requires `cloc` (https://github.com/AlDanial/cloc). Install with:
#   sudo apt install -y cloc

set -euo pipefail

if ! command -v cloc >/dev/null 2>&1; then
  echo "ERROR: cloc is not installed. Install it with: sudo apt install -y cloc" >&2
  exit 1
fi

CLOC_OPTS=(--exclude-dir=__pycache__,.venv --quiet)

echo "=================================================================="
echo " Function Calling architecture — llm-integrations/function_calling/"
echo "=================================================================="
cloc "${CLOC_OPTS[@]}" function_calling/

echo
echo "=================================================================="
echo " MCP architecture — llm-integrations/mcp_server/"
echo "=================================================================="
cloc "${CLOC_OPTS[@]}" mcp_server/

echo
echo "=================================================================="
echo " Shared REST invocation logic (NOT counted per-architecture) —"
echo " llm-integrations/common/"
echo "=================================================================="
cloc "${CLOC_OPTS[@]}" common/

echo
echo "=================================================================="
echo " Shared agent orchestrator (NOT counted per-architecture) —"
echo " llm-integrations/orchestrator/"
echo "=================================================================="
cloc "${CLOC_OPTS[@]}" orchestrator/

echo
echo "=================================================================="
echo " Combined: Function Calling + shared common/ (what a developer would"
echo " actually have to write/maintain end-to-end for this architecture)"
echo "=================================================================="
cloc "${CLOC_OPTS[@]}" function_calling/ common/

echo
echo "=================================================================="
echo " Combined: MCP + shared common/"
echo "=================================================================="
cloc "${CLOC_OPTS[@]}" mcp_server/ common/
