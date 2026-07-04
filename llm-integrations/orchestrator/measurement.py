"""Measurement instrumentation for the Function Calling vs MCP experiment.

Exports two artifacts per orchestrator run, without touching any
microservice business logic (purely client-side, in the orchestrator):

1. A single append-only CSV (`experiments/results/runs.csv`) with one row
   per run — the primary input for the statistical analysis (n=5 reps x
   3 scenarios x 2 architectures x schema variants).
2. A per-run JSON file (`experiments/results/<run_id>.json`) with full
   detail (every tool call, its arguments, result and latency), useful for
   debugging a specific run without re-executing it.

Column/field names are stable and documented here so the user's later
pandas analysis can rely on them.
"""

import csv
import json
import time
import uuid
from dataclasses import asdict
from pathlib import Path

from orchestrator.agent import RunResult

CSV_FIELDNAMES = [
    "run_id",
    "timestamp_utc",
    "mode",
    "scenario",
    "schema_variant",
    "llm_round_trips",
    "tool_call_count",
    "total_latency_ms",
    "tool_latency_ms_sum",
    "had_error",
]


def _is_error_run(result: RunResult) -> bool:
    if result.final_text.startswith("ERROR:"):
        return True
    return any("error" in call.result for call in result.tool_calls if isinstance(call.result, dict))


def record_run(
    result: RunResult,
    scenario: str,
    schema_variant: str,
    output_dir: Path,
) -> str:
    """Append a summary row to `runs.csv` and write a detailed JSON file for
    this run. Returns the generated `run_id`.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"
    timestamp_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    tool_latency_sum = sum(call.latency_ms for call in result.tool_calls)
    row = {
        "run_id": run_id,
        "timestamp_utc": timestamp_utc,
        "mode": result.mode,
        "scenario": scenario,
        "schema_variant": schema_variant,
        "llm_round_trips": result.llm_round_trips,
        "tool_call_count": len(result.tool_calls),
        "total_latency_ms": round(result.total_latency_ms, 2),
        "tool_latency_ms_sum": round(tool_latency_sum, 2),
        "had_error": _is_error_run(result),
    }

    csv_path = output_dir / "runs.csv"
    is_new_file = not csv_path.exists()
    with csv_path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        if is_new_file:
            writer.writeheader()
        writer.writerow(row)

    detail_path = output_dir / f"{run_id}.json"
    detail = {
        **row,
        "final_text": result.final_text,
        "tool_calls": [asdict(call) for call in result.tool_calls],
    }
    detail_path.write_text(json.dumps(detail, indent=2, default=str))

    return run_id
