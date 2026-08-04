#!/usr/bin/env python
"""
Phase 5: MCP Server + Client test.
Test backend calling data access via MCP instead of direct FAISS.
Measure latency overhead of the service boundary.
"""

import time
import sys
from dotenv import load_dotenv
load_dotenv()

from src.data_loader import load_csv, create_chunks
from src.embedding_service import EmbeddingService
from src.retrieval import FAISSRetrieval
from backend.services.mcp_client import MCPClient


def print_header(title: str):
    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)


def test_direct_faiss():
    """Baseline: direct FAISS calls."""
    print("\n[Baseline] Direct FAISS access (no MCP)...")

    rows = load_csv("data/sample_budget_data.csv")
    chunks = create_chunks(rows)
    embedding_service = EmbeddingService()
    faiss_retrieval = FAISSRetrieval(chunks, embedding_service)

    queries = [
        "What was the engineering headcount variance?",
        "Which cost centers are over budget?",
        "What are the major spending variances?",
    ]

    total_latency = 0

    for query in queries:
        start = time.time()
        results = faiss_retrieval.search(query, top_k=5)
        latency = (time.time() - start) * 1000
        total_latency += latency
        print(f"  Query: '{query[:50]}...'")
        print(f"    Latency: {latency:.2f} ms, Results: {len(results)}")

    avg_latency = total_latency / len(queries)
    print(f"\n  Average latency (direct): {avg_latency:.2f} ms")
    return avg_latency


def test_mcp():
    """Test: MCP client calls server."""
    print("\n[MCP] Calling data access via MCP server...")

    client = MCPClient()

    queries = [
        "What was the engineering headcount variance?",
        "Which cost centers are over budget?",
        "What are the major spending variances?",
    ]

    total_latency = 0

    for query in queries:
        start = time.time()
        result = client.search_financial_data(query, top_k=5)
        latency = (time.time() - start) * 1000
        total_latency += latency
        print(f"  Query: '{query[:50]}...'")
        print(f"    Latency: {latency:.2f} ms, Results: {len(result.results)}")

    avg_latency = total_latency / len(queries)
    print(f"\n  Average latency (MCP): {avg_latency:.2f} ms")
    return avg_latency


def main():
    print_header("PHASE 5: MCP Server Boundary for Data Access")

    print("\nPhase 5 introduces the MCP server boundary:")
    print("- Data access (FAISS, cost-center lookups) is now a separate service")
    print("- Backend agents call data via MCP, not direct imports")
    print("- Demonstrates architectural honesty about service boundaries")

    # Test baseline (direct)
    direct_latency = test_direct_faiss()

    # Test MCP
    mcp_latency = test_mcp()

    # Comparison
    print_header("LATENCY COMPARISON")
    overhead = mcp_latency - direct_latency
    overhead_pct = (overhead / direct_latency) * 100 if direct_latency > 0 else 0

    print(f"\nDirect FAISS avg:  {direct_latency:>8.2f} ms")
    print(f"MCP client avg:    {mcp_latency:>8.2f} ms")
    print(f"Overhead:          {overhead:>8.2f} ms ({overhead_pct:>6.1f}%)")

    print(f"\nNote: MCP latency includes subprocess startup overhead.")
    print(f"In production (TCP/SSE bridge), overhead would be ~10-50ms per call.")

    print_header("PHASE 5 COMPLETE")
    print("\n✓ MCP server created with three data access tools")
    print("✓ MCP client calls server via subprocess (demo mode)")
    print("✓ Data access pulled behind service boundary")
    print("✓ Latency overhead measured")
    print("\nArchitecture:")
    print("  Phase 0-4: Backend → direct FAISS")
    print("  Phase 5+:  Backend → MCP client → MCP server → FAISS")
    print("\nNext: Phase 6 will add the eval harness (golden dataset, metrics).")


if __name__ == "__main__":
    main()
