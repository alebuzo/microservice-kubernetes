"""Shared agent orchestrator: drives a Claude conversation with tool use,
delegating tool execution to either the Function Calling or the MCP
backend depending on `--mode`. Model, temperature, system prompt and the
conversation loop itself are identical between modes (see `config.py`) —
the only thing that changes is which backend supplies/executes the tools.

Usage:
    cd llm-integrations
    source .venv/bin/activate
    export ANTHROPIC_API_KEY="sk-ant-..."
    python -m orchestrator.agent --mode function_calling --prompt "..."
    python -m orchestrator.agent --mode mcp --prompt "..."

Requires the target services reachable at the URLs configured in
`common/services.py` (defaults assume `kubectl port-forward` on
18081/18082/18083, see `experiments/baseline_contracts.md`).
"""

import argparse
import asyncio
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any

from anthropic import AsyncAnthropic

from orchestrator.backends import make_backend
from orchestrator.config import (
    MAX_TOKENS,
    MAX_TOOL_ITERATIONS,
    MODEL,
    SYSTEM_PROMPT,
    TEMPERATURE,
)


@dataclass
class ToolCallRecord:
    name: str
    arguments: dict
    result: dict
    latency_ms: float


@dataclass
class RunResult:
    """Everything a caller (CLI, scenario script, or the future measurement
    layer) needs: the final answer plus enough structured detail about the
    run to log latency and tool-call counts without re-instrumenting this
    module later.
    """

    mode: str
    final_text: str
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    total_latency_ms: float = 0.0
    llm_round_trips: int = 0


async def run_conversation(mode: str, user_prompt: str) -> RunResult:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set in this shell.")

    client = AsyncAnthropic(api_key=api_key)
    tool_calls: list[ToolCallRecord] = []
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_prompt}]

    start = time.perf_counter()
    llm_round_trips = 0

    async with make_backend(mode) as backend:
        for _ in range(MAX_TOOL_ITERATIONS):
            response = await client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                system=SYSTEM_PROMPT,
                tools=backend.tools,
                messages=messages,
            )
            llm_round_trips += 1
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                final_text = "".join(
                    block.text for block in response.content if block.type == "text"
                ).strip()
                total_latency_ms = (time.perf_counter() - start) * 1000
                return RunResult(
                    mode=mode,
                    final_text=final_text,
                    tool_calls=tool_calls,
                    total_latency_ms=total_latency_ms,
                    llm_round_trips=llm_round_trips,
                )

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                call_start = time.perf_counter()
                result = await backend.call_tool(block.name, block.input)
                call_latency_ms = (time.perf_counter() - call_start) * 1000
                tool_calls.append(
                    ToolCallRecord(
                        name=block.name,
                        arguments=block.input,
                        result=result,
                        latency_ms=call_latency_ms,
                    )
                )
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                    }
                )
            messages.append({"role": "user", "content": tool_results})

    total_latency_ms = (time.perf_counter() - start) * 1000
    return RunResult(
        mode=mode,
        final_text=f"ERROR: exceeded MAX_TOOL_ITERATIONS ({MAX_TOOL_ITERATIONS}) without a final answer.",
        tool_calls=tool_calls,
        total_latency_ms=total_latency_ms,
        llm_round_trips=llm_round_trips,
    )


def _print_result(result: RunResult) -> None:
    print(f"Mode: {result.mode}")
    print(f"LLM round trips: {result.llm_round_trips}")
    print(f"Tool calls ({len(result.tool_calls)}):")
    for call in result.tool_calls:
        print(f"  - {call.name}({call.arguments}) -> {call.result}  [{call.latency_ms:.1f} ms]")
    print(f"Total latency: {result.total_latency_ms:.1f} ms")
    print(f"\nFinal answer:\n{result.final_text}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Function Calling vs MCP agent orchestrator")
    parser.add_argument("--mode", choices=["function_calling", "mcp"], required=True)
    parser.add_argument("--prompt", required=True, help="User task for the agent to perform")
    parser.add_argument(
        "--scenario",
        choices=["bajo", "medio", "alto", "manual"],
        default="manual",
        help="Which methodology scenario this run belongs to (default: manual, for ad-hoc testing)",
    )
    parser.add_argument(
        "--schema-variant",
        default="baseline",
        help="Schema variant label for this run, e.g. 'baseline', 'itemid-rename', "
        "'price-nested', 'payment-method' (default: baseline)",
    )
    parser.add_argument(
        "--log-dir",
        default=None,
        help="Directory to write runs.csv + per-run JSON detail into "
        "(default: <repo>/llm-integrations/experiments/results)",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Skip writing measurement output (useful for quick manual checks)",
    )
    args = parser.parse_args()

    try:
        result = asyncio.run(run_conversation(args.mode, args.prompt))
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    _print_result(result)

    if not args.no_log:
        from pathlib import Path

        from orchestrator.measurement import record_run

        log_dir = (
            Path(args.log_dir)
            if args.log_dir
            else Path(__file__).resolve().parent.parent / "experiments" / "results"
        )
        run_id = record_run(result, args.scenario, args.schema_variant, log_dir)
        print(f"\nLogged run '{run_id}' to {log_dir}/runs.csv")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
