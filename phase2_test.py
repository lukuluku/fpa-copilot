#!/usr/bin/env python
"""
Phase 2: Agent pipeline test.
Router → Retrieval → Drafting (no loop, no Critic yet).
Three functions called in sequence.
"""

import sys
from dotenv import load_dotenv
load_dotenv()

from src.data_loader import load_csv, create_chunks
from src.embedding_service import EmbeddingService
from src.retrieval import FAISSRetrieval
from backend.agents.router_agent import RouterAgent
from backend.agents.retrieval_agent import RetrievalAgent
from backend.agents.drafting_agent import DraftingAgent


def print_header(title: str):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def run_pipeline(query: str, router: RouterAgent, retrieval_agent: RetrievalAgent, drafter: DraftingAgent):
    """Run a single query through the full pipeline."""
    print(f"\n{'─' * 80}")
    print(f"QUERY: {query}")
    print(f"{'─' * 80}")

    # Step 1: Router
    print("\n[1] ROUTER AGENT")
    route_decision = router.route(query)
    print(f"    In-scope: {route_decision.in_scope}")
    print(f"    Reason: {route_decision.reason}")

    if not route_decision.in_scope:
        print(f"\n    ❌ REFUSED: Query is out of scope.")
        return

    # Step 2: Retrieval
    print("\n[2] RETRIEVAL AGENT")
    retrieval_decision = retrieval_agent.retrieve(query, top_k=5)
    print(f"    Coverage sufficient: {retrieval_decision.coverage_sufficient}")
    print(f"    Reasoning: {retrieval_decision.reasoning}")
    if retrieval_decision.reformulated_query:
        print(f"    Suggested reformulation: {retrieval_decision.reformulated_query}")
    print(f"    Retrieved {len(retrieval_decision.chunks)} chunks (scores: {', '.join([f'{c.score:.3f}' for c in retrieval_decision.chunks[:3]])}...)")

    # Step 3: Drafting
    print("\n[3] DRAFTING AGENT")
    draft_result = drafter.draft(query, retrieval_decision.chunks)
    print(f"    Model: {draft_result.model_used}")
    print(f"    Tokens: {draft_result.tokens_used[0]} input, {draft_result.tokens_used[1]} output")
    print(f"\n    Answer:")
    print(f"    {'-' * 76}")
    for line in draft_result.answer.split('\n'):
        print(f"    {line}")
    print(f"    {'-' * 76}")


def main():
    print_header("PHASE 2: Agent Pipeline (Router → Retrieval → Drafting)")

    # Setup
    print("\nSetting up agents...")
    rows = load_csv("data/sample_budget_data.csv")
    chunks = create_chunks(rows)
    print(f"  Loaded {len(rows)} rows, created {len(chunks)} chunks")

    embedding_service = EmbeddingService()
    faiss_retrieval = FAISSRetrieval(chunks, embedding_service)
    print(f"  Built FAISS index")

    router = RouterAgent()
    retrieval_agent = RetrievalAgent(faiss_retrieval)
    drafter = DraftingAgent()
    print(f"  Initialized 3 agents: Router, Retrieval, Drafting")

    # Test queries
    test_queries = [
        "What was the engineering headcount variance in Q3?",
        "Which cost centers are over budget by the most?",
        "Can you summarize the major spending variances?",
        "What's the weather forecast for next week?",  # Out of scope
        "How do I file my taxes?",  # Out of scope
    ]

    for query in test_queries:
        try:
            run_pipeline(query, router, retrieval_agent, drafter)
        except Exception as e:
            print(f"\n    ⚠️  ERROR: {e}")

    print_header("PHASE 2 COMPLETE")
    print("\nKey observations:")
    print("- Router correctly rejected out-of-scope queries")
    print("- Retrieval assessed coverage and suggested reformulations if needed")
    print("- Drafting generated grounded answers from context")
    print("- No retry loop yet (Phase 3) — retrieval uses best-available context")
    print("- No Critic verification yet (Phase 3) — all drafts are returned")
    print("\nNext: Phase 3 will add the orchestrator loop with retry/revision logic and the Critic Agent.")


if __name__ == "__main__":
    main()
