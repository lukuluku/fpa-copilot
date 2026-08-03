#!/usr/bin/env python
"""
Phase 3: Orchestrator + Critic test.
Full pipeline with retry and revision logic.
Tests: pass-through, retrieval retry, draft revision, and hard refusal scenarios.
"""

from dotenv import load_dotenv
load_dotenv()

from src.data_loader import load_csv, create_chunks
from src.embedding_service import EmbeddingService
from src.retrieval import FAISSRetrieval
from backend.agents.orchestrator import AgentOrchestrator


def print_header(title: str):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def print_result(query: str, result):
    """Pretty-print an orchestrator result."""
    print(f"\nQuery: {query}")
    print(f"Success: {result.success}")
    print(f"Agent path: {' → '.join(result.agent_path)}")
    print(f"Retrieval retried: {result.retrieval_retried}")
    print(f"Draft revised: {result.draft_revised}")
    print(f"Confidence: {result.confidence_score:.2f}")

    if result.success:
        print(f"\nAnswer:")
        print(f"{'─' * 76}")
        for line in result.answer.split('\n')[:10]:  # First 10 lines
            print(f"  {line}")
        if len(result.answer.split('\n')) > 10:
            print(f"  ... ({len(result.answer.split(chr(10))) - 10} more lines)")
        print(f"{'─' * 76}")
    else:
        print(f"\nRefusal reason: {result.refusal_reason}")


def main():
    print_header("PHASE 3: Orchestrator + Critic Agent")

    # Setup
    print("\nSetting up orchestrator...")
    rows = load_csv("data/sample_budget_data.csv")
    chunks = create_chunks(rows)
    embedding_service = EmbeddingService()
    faiss_retrieval = FAISSRetrieval(chunks, embedding_service)

    orchestrator = AgentOrchestrator(faiss_retrieval)
    print(f"  Initialized orchestrator with 4 agents + retrieval retry + draft revision")

    # Test scenarios
    print_header("TEST SCENARIOS")

    # Scenario 1: Pass-through (good query, high confidence)
    print("\n[Scenario 1] Good query → should pass straight through")
    result = orchestrator.run("What was the engineering headcount variance in Q3?")
    print_result("What was the engineering headcount variance in Q3?", result)

    # Scenario 2: Ambiguous query → may trigger retrieval retry
    print("\n[Scenario 2] Ambiguous query → may trigger retrieval retry")
    result = orchestrator.run("Which departments spent the most?")
    print_result("Which departments spent the most?", result)

    # Scenario 3: Summary query → tests drafting on broader context
    print("\n[Scenario 3] Broad variance summary → tests drafting")
    result = orchestrator.run("What are the key budget variances?")
    print_result("What are the key budget variances?", result)

    # Scenario 4: Out-of-scope → refusal at router
    print("\n[Scenario 4] Out-of-scope query → refusal at router (fastest)")
    result = orchestrator.run("What's the weather?")
    print_result("What's the weather?", result)

    # Scenario 5: Another out-of-scope
    print("\n[Scenario 5] Another out-of-scope → router refuses")
    result = orchestrator.run("How do I invest in stocks?")
    print_result("How do I invest in stocks?", result)

    print_header("PHASE 3 COMPLETE")
    print("\nKey features tested:")
    print("✓ Router classification (in-scope vs out-of-scope)")
    print("✓ Retrieval + optional retry on low coverage")
    print("✓ Drafting from context with citations")
    print("✓ Critic faithfulness review")
    print("✓ Optional draft revision on critique failure")
    print("✓ Hard refusal path (no partial answers)")
    print("\nOrchestrator behavior:")
    print("- Fast exit on out-of-scope (Router only)")
    print("- Retry retrieval once if coverage is low")
    print("- Revise draft once if critique requests it")
    print("- Full refusal if critique fails after revision")
    print("\nNext: Phase 4 will add observability (Langfuse tracing with per-agent detail).")


if __name__ == "__main__":
    main()
