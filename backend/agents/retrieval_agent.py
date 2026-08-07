"""
Retrieval Agent — Search for relevant context and assess coverage.

Phase 5: accepts either a FAISSRetrieval (direct, fast, dev default) or an
MCPClient (service boundary, subprocess overhead in demo mode). Pass
use_mcp=True to route through the MCP server instead of calling FAISS directly.
"""

import json
import yaml
from pathlib import Path
from dataclasses import dataclass
from src.retrieval import FAISSRetrieval, RetrievalResult
from backend.services.llm_gateway import get_llm_gateway


@dataclass
class RetrievalDecision:
    """Decision from the Retrieval Agent."""
    chunks: list[RetrievalResult]
    coverage_sufficient: bool
    reformulated_query: str | None
    reasoning: str


class RetrievalAgent:
    """
    Retrieval Agent: search for relevant chunks and assess coverage.

    Accepts either direct FAISS (fast, in-process) or MCP client (service
    boundary). The MCP path demonstrates the architecture; the direct path
    is used for eval runs and local dev where subprocess latency is unacceptable.
    """

    def __init__(self, faiss_retrieval: FAISSRetrieval, use_mcp: bool = False):
        self.faiss = faiss_retrieval
        self.use_mcp = use_mcp
        self.llm = get_llm_gateway()
        self.prompt_template = self._load_prompt()

        if use_mcp:
            from backend.services.mcp_client import MCPClient
            self._mcp = MCPClient()
        else:
            self._mcp = None

    def _load_prompt(self) -> dict:
        """Load retrieval prompt template."""
        prompt_file = Path("backend/prompts/retrieval_v1.yaml")
        with open(prompt_file) as f:
            return yaml.safe_load(f)

    def _search(self, query: str, top_k: int) -> list[RetrievalResult]:
        """
        Route search to MCP server or direct FAISS depending on use_mcp flag.
        MCP results are reconstructed into RetrievalResult objects so the rest
        of the pipeline is unaffected by which path was taken.
        """
        if self.use_mcp:
            mcp_result = self._mcp.search_financial_data(query, top_k=top_k)
            # Reconstruct RetrievalResult objects from MCP response dicts
            reconstructed = []
            for r in mcp_result.results:
                # Build a minimal chunk-like object from the MCP response fields
                chunk = _MCPChunk(
                    chunk_id=r.get("chunk_id", ""),
                    text=r.get("text", ""),
                    source_row=r.get("source_row", {}),
                )
                reconstructed.append(_MCPRetrievalResult(chunk=chunk, score=r.get("similarity_score", 0.0)))
            return reconstructed
        else:
            return self.faiss.search(query, top_k=top_k)

    def retrieve(self, query: str, top_k: int = 5) -> RetrievalDecision:
        """
        Search for relevant chunks and assess if coverage is sufficient.
        """
        results = self._search(query, top_k)

        # Format results for the LLM to evaluate
        results_text = "\n".join(
            [f"  [{i+1}] (score: {r.score:.3f}) {r.chunk.text}" for i, r in enumerate(results)]
        )

        system = self.prompt_template["system"]
        user_template = self.prompt_template["user_template"]
        user = user_template.format(query=query, results=results_text)

        response = self.llm.sync_complete(
            system=system,
            user=user,
            temperature=0.0,  # Deterministic coverage assessment
            max_tokens=512,
        )

        try:
            # Strip markdown code fences if present
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```", 2)[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            result = json.loads(text)
            return RetrievalDecision(
                chunks=results,
                coverage_sufficient=result.get("coverage_sufficient", False),
                reformulated_query=result.get("reformulated_query"),
                reasoning=result.get("reasoning", "Unknown"),
            )
        except json.JSONDecodeError:
            # Fallback: low coverage if parsing fails
            return RetrievalDecision(
                chunks=results,
                coverage_sufficient=False,
                reformulated_query=None,
                reasoning=f"Failed to parse retrieval response: {response.text}",
            )


@dataclass
class _MCPChunk:
    """Minimal chunk-like object reconstructed from MCP response."""
    chunk_id: str
    text: str
    source_row: dict


@dataclass
class _MCPRetrievalResult:
    """Minimal RetrievalResult-like object reconstructed from MCP response."""
    chunk: _MCPChunk
    score: float


if __name__ == "__main__":
    from src.data_loader import load_csv, create_chunks
    from src.embedding_service import EmbeddingService

    rows = load_csv("data/sample_budget_data.csv")
    chunks = create_chunks(rows)
    embedding_service = EmbeddingService()
    faiss_retrieval = FAISSRetrieval(chunks, embedding_service)

    test_queries = [
        "What was the engineering payroll variance in Q3?",
        "Which departments spent too much?",
    ]

    print("--- Direct FAISS ---")
    agent_direct = RetrievalAgent(faiss_retrieval, use_mcp=False)
    for query in test_queries:
        decision = agent_direct.retrieve(query)
        print(f"\nQuery: {query}")
        print(f"Coverage sufficient: {decision.coverage_sufficient}")
        print(f"Reasoning: {decision.reasoning}")

    print("\n--- Via MCP ---")
    agent_mcp = RetrievalAgent(faiss_retrieval, use_mcp=True)
    for query in test_queries:
        decision = agent_mcp.retrieve(query)
        print(f"\nQuery: {query}")
        print(f"Coverage sufficient: {decision.coverage_sufficient}")
        print(f"Reasoning: {decision.reasoning}")
