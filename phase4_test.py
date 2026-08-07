#!/usr/bin/env python3
"""
Phase 4: Langfuse observability test.

Runs two queries through the full orchestrator and verifies:
  1. Local JSON trace is written with correct per_agent entries.
  2. If LANGFUSE_ENABLED=true and keys are set, confirms Langfuse accepted
     the trace (via get_trace_url printed for manual verification).

Run with local-only (default):
    python phase4_test.py

Run with Langfuse enabled:
    LANGFUSE_ENABLED=true \
    LANGFUSE_PUBLIC_KEY=pk-lf-... \
    LANGFUSE_SECRET_KEY=sk-lf-... \
    python phase4_test.py
"""

import glob
import json
import os

from dotenv import load_dotenv
load_dotenv()

from src.data_loader import load_csv, create_chunks
from src.embedding_service import EmbeddingService
from src.retrieval import FAISSRetrieval
from backend.agents.orchestrator import AgentOrchestrator
from backend.services.trace_emitter import TraceEmitter


def _latest_trace() -> dict:
    files = sorted(glob.glob("traces/trace_*.json"), key=os.path.getmtime)
    with open(files[-1]) as f:
        return json.load(f)


def assert_trace_schema(trace: dict, label: str) -> None:
    """Spot-check the §3.6 fields we care about."""
    required = [
        "trace_id", "session_id", "timestamp", "query",
        "agent_path", "retrieval_retried", "draft_revised",
        "outcome", "per_agent", "total_cost_usd", "total_latency_ms",
    ]
    missing = [k for k in required if k not in trace]
    assert not missing, f"[{label}] Missing §3.6 fields: {missing}"

    for step in trace["per_agent"]:
        for field in ("agent", "model", "latency_ms", "input_tokens", "output_tokens", "cost_usd"):
            assert field in step, f"[{label}] per_agent step missing '{field}': {step}"

    assert trace["total_cost_usd"] > 0, f"[{label}] total_cost_usd is 0"
    assert trace["total_latency_ms"] > 0, f"[{label}] total_latency_ms is 0"
    print(f"  [OK] [{label}] schema valid -- {len(trace['per_agent'])} per_agent entries, "
          f"total_cost=${trace['total_cost_usd']:.5f}, outcome={trace['outcome']}")


def main():
    print("=" * 70)
    print("PHASE 4: Langfuse Observability")
    print("=" * 70)

    rows = load_csv("data/sample_budget_data.csv")
    chunks = create_chunks(rows)
    emb = EmbeddingService()
    faiss = FAISSRetrieval(chunks, emb)
    emitter = TraceEmitter()
    orchestrator = AgentOrchestrator(faiss, trace_emitter=emitter)

    langfuse_on = emitter.langfuse_enabled
    print(f"\nLangfuse enabled: {langfuse_on}")
    if langfuse_on:
        print(f"  host: {os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')}")

    # Test 1: standard in-scope query
    print("\n[Test 1] Standard Q&A query")
    result = orchestrator.run("What was the engineering headcount variance in Q3?")
    trace = _latest_trace()
    print(f"  outcome=success:{result.success}, path={' -> '.join(result.agent_path)}")
    assert_trace_schema(trace, "Test 1")

    # Test 2: out-of-scope -- router-only path, one per_agent entry
    print("\n[Test 2] Out-of-scope query -- router-only path")
    result = orchestrator.run("What's the best restaurant in London?")
    trace = _latest_trace()
    assert not result.success
    assert trace["outcome"] == "refused_scope"
    agents_seen = [s["agent"] for s in trace["per_agent"]]
    assert agents_seen == ["router"], f"Expected ['router'], got: {agents_seen}"
    assert_trace_schema(trace, "Test 2")

    # Summary
    print("\n" + "-" * 70)
    summary = emitter.get_summary()
    print("Session summary:")
    for k, v in summary.items():
        print(f"  {k:<22}: {v:.5f}" if isinstance(v, float) else f"  {k:<22}: {v}")

    if langfuse_on and emitter._langfuse:
        url = emitter._langfuse.get_trace_url(trace_id=getattr(emitter, "_last_trace_id", None))
        print(f"\nLangfuse trace URL (most recent): {url}")

    print("\nPhase 4 complete -- all assertions passed")
    if not langfuse_on:
        print("\nNote: Langfuse remote emission not tested.")
        print("Set LANGFUSE_ENABLED=true + keys to test it.")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
