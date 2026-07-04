"""Verify Anthropic API access for the Function Calling vs MCP experiment.

Usage:
    source llm-integrations/.venv/bin/activate
    export ANTHROPIC_API_KEY="sk-ant-..."   # never write this to a file in the repo
    python llm-integrations/orchestrator/verify_api_access.py

This performs a minimal, low-cost request against the fixed experimental model
(claude-sonnet-4-6) to confirm that:
  1. ANTHROPIC_API_KEY is set and valid.
  2. The SDK can reach the Anthropic API from this environment.
  3. The exact model id used throughout the experiment is available to this key.
"""

import os
import sys

MODEL = "claude-sonnet-4-6"


def main() -> int:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "ERROR: ANTHROPIC_API_KEY is not set in this shell.\n"
            "Set it with: export ANTHROPIC_API_KEY=\"sk-ant-...\"\n"
            "Never hardcode it in a file inside the repository.",
            file=sys.stderr,
        )
        return 1

    try:
        import anthropic
    except ImportError:
        print(
            "ERROR: the 'anthropic' package is not installed in this environment.\n"
            "Install it with: pip install -r llm-integrations/requirements.txt",
            file=sys.stderr,
        )
        return 1

    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=16,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
        )
    except anthropic.APIStatusError as exc:
        print(f"ERROR: API call failed with status {exc.status_code}: {exc.message}", file=sys.stderr)
        return 1
    except anthropic.APIConnectionError as exc:
        print(f"ERROR: could not connect to the Anthropic API: {exc}", file=sys.stderr)
        return 1

    text = "".join(block.text for block in response.content if block.type == "text").strip()
    print(f"Model: {response.model}")
    print(f"Stop reason: {response.stop_reason}")
    print(f"Response: {text!r}")
    print(f"Usage: input_tokens={response.usage.input_tokens}, output_tokens={response.usage.output_tokens}")
    print("\nSUCCESS: Anthropic API access verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
