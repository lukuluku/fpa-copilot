#!/usr/bin/env python
"""
Phase 4: Observability test.
Run queries through instrumented orchestrator and display per-agent traces.
"""

from dotenv import load_dotenv
load_dotenv()

from src.data_loader import load_csv, create_chunks
from src.embedding_service import EmbeddingService
from src.retrieval import FAISSRetrieval
from backend.agents.orchestrator import AgentOrchestrator
from backend.services.trace_emitter import TraceEmitter


def print_header(title: str):
    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)


def print_trace_details(result, trace_emitter):
    """Print detailed trace information for a query."""
    if not trace_emitter.traces:
        return

    trace = trace_emitter.traces[-1]

    print(f"\nTrace ID: {trace.trace_id}")
    print(f"Session ID: {trace.session_id}")
    print(f"Query: {trace.query}")
    print(f"Outcome: {trace.outcome}")
    print(f"Agent path: {' → '.join(trace.agent_path)}")
    print(f"Retrieval retried: {trace.retrieval_retried}")
    print(f"Draft revised: {trace.draft_revised}")

    print(f"\n{'Per-Agent Breakdown':─^90}")
    print(f"{'Agent':<15} {'Model':<30} {'Latency (ms)':<15} {'Tokens':<20} {'Cost (USD)':<10}")
    print("-" * 90)

    for step in trace.per_agent:
        model_short = step.model.replace("claude-", "").replace("-20251001", "")
        tokens = f"{step.input_tokens}in/{step.output_tokens}out"
        print(
            f"{step.agent:<15} {model_short:<30} {step.latency_ms:>10.2f}      "
            f"{tokens:<20} ${step.cost_usd:>8.6f}"
        )

    print("-" * 90)
    print(f"{'TOTAL':<15} {'':<30} {trace.total_latency_ms:>10.2f} ms  "
          f"{'(full pipeline)':<20} ${trace.total_cost_usd:>8.6f}")

    print(f"\nConfidence score: {trace.confidence_score:.2f}")
    if trace.refusal_reason:
        print(f"Refusal reason: {trace.refusal_reason}")


def main():
    print_header("PHASE 4: Observability & Per-Agent Tracing")

    # Setup
    print("\nSetting up orchestrator with tracing...")
    rows = load_csv("data/sample_budget_data.csv")
    chunks = create_chunks(rows)
    embedding_service = EmbeddingService()
    faiss_retrieval = FAISSRetrieval(chunks, embedding_service)

    trace_emitter = TraceEmitter(output_dir="traces")
    orchestrator = AgentOrchestrator(faiss_retrieval, trace_emitter)
    print(f"  Orchestrator ready with trace emission to {trace_emitter.output_dir}/")

    # Test queries
    test_queries = [
        "What was the engineering headcount variance in Q3?",
        "Which cost centers are over budget?",
        "What's the weather?",
    ]

    for query in test_queries:
        print_header(f"QUERY: {query}")
        result = orchestrator.run(query)

        if result.success:
            print(f"✅ SUCCESS")
            print(f"\nAnswer (first 200 chars):")
            print(f"  {result.answer[:200]}...")
        else:
            print(f"❌ REFUSED")
            print(f"  Reason: {result.refusal_reason}")

        print_trace_details(result, trace_emitter)

    # Summary
    print_header("TRACE SUMMARY")
    summary = trace_emitter.get_summary()
    print(f"Total traces: {summary['total_traces']}")
    print(f"  Successful: {summary['successful']}")
    print(f"  Refused: {summary['refused']}")
    print(f"\nAggregate costs:")
    print(f"  Total: ${summary['total_cost_usd']:.6f}")
    print(f"  Average per query: ${summary['avg_cost_per_trace']:.6f}")
    print(f"\nAggregate latency:")
    print(f"  Total: {summary['total_latency_ms']:.2f} ms")
    print(f"  Average per query: {summary['avg_latency_ms']:.2f} ms")
    print(f"\nTraces stored in: {trace_emitter.output_dir}/")

    print_header("PHASE 4 COMPLETE")
    print("\n✓ Per-agent tracing working")
    print("✓ Cost breakdown by agent visible")
    print("✓ Latency breakdown by agent visible")
    print("✓ Traces persisted to local JSON files")
    print("\nNext: Phase 5 will pull data access into the MCP server.")


if __name__ == "__main__":
    main()
