#!/usr/bin/env python
"""
Phase 1: Retrieval test.
Load finance data, build FAISS index, test retrieval with 3+ queries.
Observe what works, what fails, and what low-coverage retrieval looks like.
"""

import sys
from src.data_loader import load_csv, create_chunks
from src.embedding_service import EmbeddingService
from src.retrieval import FAISSRetrieval


def print_header(title: str):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def test_query(retrieval: FAISSRetrieval, query: str, expected: str, top_k: int = 5):
    """Run a single test query and print results."""
    print(f"\nQuery: {query}")
    print(f"Expected: {expected}")
    print(f"\nTop {top_k} results:")

    results = retrieval.search(query, top_k=top_k)

    for i, result in enumerate(results, 1):
        print(f"\n  {i}. [Score: {result.score:.3f}] {result.chunk.text}")

    if results:
        coverage = results[0].score
        print(f"\nBest match score: {coverage:.3f}")
        if coverage < 0.5:
            print("  ⚠️  LOW COVERAGE: score is weak, retrieval struggled to find a good match")
        elif coverage < 0.7:
            print("  ⚠️  MEDIUM COVERAGE: acceptable but not strong")
        else:
            print("  ✅ GOOD COVERAGE: strong match")
    else:
        print("  ❌ NO RESULTS: retrieval returned nothing")


def main():
    print_header("PHASE 1: Retrieval with FAISS + Embeddings")

    # Load data
    print("\n1. Loading finance data...")
    rows = load_csv("data/sample_budget_data.csv")
    print(f"   Loaded {len(rows)} rows")

    # Create chunks
    print("\n2. Creating chunks...")
    chunks = create_chunks(rows)
    print(f"   Created {len(chunks)} chunks")

    # Build retrieval index
    print("\n3. Building FAISS index (this embeds all chunks)...")
    embedding_service = EmbeddingService()
    retrieval = FAISSRetrieval(chunks, embedding_service)

    # Test queries
    print_header("RETRIEVAL TEST QUERIES")

    # Test 1: Direct match (should work well)
    test_query(
        retrieval,
        "What was the engineering payroll variance in Q3?",
        "Expected: High coverage. Should find the Engineering payroll chunk with -5.6% variance."
    )

    # Test 2: Broader/ambiguous query (should have lower coverage)
    test_query(
        retrieval,
        "Which departments spent too much money?",
        "Expected: Medium-to-low coverage. Query is ambiguous (which threshold? which departments?). "
        "Retrieval should find cost centers with negative variance but confidence will be lower."
    )

    # Test 3: Out-of-scope query (should fail badly)
    test_query(
        retrieval,
        "What's the weather forecast for next week?",
        "Expected: Low-to-zero coverage. Completely out of domain (finance data). "
        "Retrieval will return *something* (FAISS always returns k results) but scores will be very low."
    )

    print_header("PHASE 1 COMPLETE")
    print("\nKey observations:")
    print("- FAISS always returns k results, even for nonsense queries (it can't refuse)")
    print("- Score < 0.5 signals weak retrieval coverage — should be flagged for retry or escalation")
    print("- The orchestrator (Phase 2) will use these scores to decide whether to retry or refuse")
    print("\nNext: Phase 2 will add the Router, Retrieval, Drafting, and Critic agents.")


if __name__ == "__main__":
    main()
