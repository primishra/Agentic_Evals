#!/usr/bin/env python3
"""Run the Tool Use Benchmark against both agent adapters and write scored
results + aggregate metrics to results/.

Usage:
    export GROQ_API_KEY=...
    python run_pilot.py

Requires: langchain-core, langchain-groq, groq, pydantic (see repo requirements).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "harness"))
sys.path.insert(0, str(HERE / "harness" / "agents"))

import runner  # noqa: E402
import scorer  # noqa: E402
import langchain_groq_agent as agent_a  # noqa: E402
import manual_react_agent as agent_b  # noqa: E402


def compute_summary(
    agent_id: str,
    model: str,
    scores: List[Dict[str, Any]],
    traces: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute and print aggregate metrics for one agent."""
    total = len(scores)
    completed = sum(1 for s in scores if s["task_completion"] is True)
    needs_review = sum(1 for s in scores if s["task_completion"] == "NEEDS_REVIEW")
    mechanical = total - needs_review

    recall_vals = [s["tool_selection"] for s in scores]
    precision_vals = [s["efficiency"] for s in scores]
    avg_recall = sum(recall_vals) / len(recall_vals) if recall_vals else 0
    avg_precision = sum(precision_vals) / len(precision_vals) if precision_vals else 0

    success_rate = completed / mechanical if mechanical else 0

    total_tokens = sum(
        t.get("token_usage", {}).get("total_tokens", 0) for t in traces
    )
    avg_tokens = total_tokens / total if total else 0

    summary = {
        "agent_id": agent_id,
        "model": model,
        "total_tasks": total,
        "mechanical_pass": completed,
        "needs_review": needs_review,
        "success_rate": round(success_rate, 3),
        "tool_invocation_precision": round(avg_precision, 3),
        "tool_invocation_recall": round(avg_recall, 3),
        "total_tokens": total_tokens,
        "avg_tokens_per_task": round(avg_tokens, 1),
    }

    print(f"\n--- Summary: {agent_id} ({model}) ---")
    print(f"  Tasks run:                    {total}")
    print(f"  Mechanical pass:              {completed}/{mechanical} ({success_rate:.1%})")
    print(f"  Needs review (LLM judge):     {needs_review}")
    print(f"  Tool invocation precision:    {avg_precision:.1%}")
    print(f"  Tool invocation recall:       {avg_recall:.1%}")
    if total_tokens:
        print(f"  Total tokens:                 {total_tokens}")
        print(f"  Avg tokens per task:          {avg_tokens:.0f}")

    return summary


def main() -> None:
    if not os.environ.get("GROQ_API_KEY"):
        raise SystemExit("GROQ_API_KEY is not set.")

    tasks = json.loads((HERE / "tasks.json").read_text())
    results_dir = HERE / "results"
    results_dir.mkdir(exist_ok=True)

    all_scores = {}
    all_summaries = {}
    for agent_module in (agent_a, agent_b):
        print(f"\n=== Running {agent_module.AGENT_ID} ({agent_module.MODEL}) ===")
        traces = runner.run_agent_on_tasks(agent_module, tasks)
        (results_dir / f"{agent_module.AGENT_ID}_traces.json").write_text(
            json.dumps(traces, indent=2, default=str)
        )

        scores = scorer.score_all(tasks, traces)
        (results_dir / f"{agent_module.AGENT_ID}_scores.json").write_text(
            json.dumps(scores, indent=2, default=str)
        )
        all_scores[agent_module.AGENT_ID] = scores

        summary = compute_summary(
            agent_module.AGENT_ID, agent_module.MODEL, scores, traces
        )
        all_summaries[agent_module.AGENT_ID] = summary

    (results_dir / "all_scores.json").write_text(
        json.dumps(all_scores, indent=2, default=str)
    )
    (results_dir / "summary.json").write_text(
        json.dumps(all_summaries, indent=2, default=str)
    )
    print(f"\nWrote traces, scores, and summary to {results_dir}")


if __name__ == "__main__":
    main()
