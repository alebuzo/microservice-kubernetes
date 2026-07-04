"""Scenario runner: executes a fixed scenario prompt N times against one
architecture, logging every run via `orchestrator.measurement.record_run`.

Usage (run from `llm-integrations/`, with the target services reachable —
see `common/services.py` / `experiments/baseline_contracts.md` for the
expected `kubectl port-forward` setup):

    python -m scenarios.run_scenario --scenario bajo  --mode function_calling
    python -m scenarios.run_scenario --scenario medio --mode mcp --reps 5

For the full experiment (30 runs = 3 scenarios x 2 modes x 5 reps), use
`run_all_scenarios.sh` instead of calling this module directly per pair.
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

from orchestrator.agent import run_conversation
from orchestrator.measurement import record_run
from scenarios.prompts import SCENARIO_PROMPTS


async def run_reps(mode: str, scenario: str, reps: int, schema_variant: str, log_dir: Path) -> int:
    prompt = SCENARIO_PROMPTS[scenario]
    failures = 0
    for i in range(1, reps + 1):
        print(f"[{scenario}/{mode}/{schema_variant}] rep {i}/{reps}... ", end="", flush=True)
        start = time.perf_counter()
        try:
            result = await run_conversation(mode, prompt)
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            failures += 1
            continue
        elapsed = time.perf_counter() - start
        run_id = record_run(result, scenario, schema_variant, log_dir)
        error_flag = " [HAD ERROR]" if result.final_text.startswith("ERROR:") else ""
        print(
            f"done in {elapsed:.1f}s, {len(result.tool_calls)} tool call(s), "
            f"logged as {run_id}{error_flag}"
        )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one scenario N times against one architecture")
    parser.add_argument("--scenario", choices=list(SCENARIO_PROMPTS), required=True)
    parser.add_argument("--mode", choices=["function_calling", "mcp"], required=True)
    parser.add_argument("--reps", type=int, default=5, help="Number of repetitions (default: 5)")
    parser.add_argument(
        "--schema-variant",
        default="baseline",
        help="Schema variant label for this batch, e.g. 'baseline', 'itemid-rename', "
        "'price-nested', 'payment-method' (default: baseline)",
    )
    parser.add_argument(
        "--log-dir",
        default=None,
        help="Directory to write runs.csv + per-run JSON detail into "
        "(default: <repo>/llm-integrations/experiments/results)",
    )
    args = parser.parse_args()

    log_dir = (
        Path(args.log_dir)
        if args.log_dir
        else Path(__file__).resolve().parent.parent / "experiments" / "results"
    )

    failures = asyncio.run(run_reps(args.mode, args.scenario, args.reps, args.schema_variant, log_dir))
    if failures:
        print(f"\n{failures}/{args.reps} rep(s) failed to run (see stderr above).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
