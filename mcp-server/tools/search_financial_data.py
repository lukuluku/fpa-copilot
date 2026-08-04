"""
MCP Tool: search_financial_data
Search the financial dataset using the FAISS index.
"""

import json
from typing import Any


async def search_financial_data(
    retrieval_service: Any, query: str, top_k: int = 5
) -> dict:
    """
    Search financial data for chunks matching the query.

    Args:
        retrieval_service: FAISSRetrieval instance
        query: Natural language query
        top_k: Number of results to return

    Returns:
        Dictionary with search results and metadata
    """
    results = retrieval_service.search(query, top_k=top_k)

    return {
        "query": query,
        "top_k": top_k,
        "results": [
            {
                "chunk_id": r.chunk.chunk_id,
                "text": r.chunk.text,
                "similarity_score": r.score,
                "source_row": r.chunk.source_row,
            }
            for r in results
        ],
        "best_match_score": results[0].score if results else 0.0,
    }
