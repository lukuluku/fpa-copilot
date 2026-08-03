"""
Retrieval Agent — Search for relevant context and assess coverage.
Phase 2: No retry logic yet. Phase 3 will add the retry-once pattern.
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
    """Retrieval Agent: search for relevant chunks and assess coverage."""

    def __init__(self, faiss_retrieval: FAISSRetrieval):
        self.faiss = faiss_retrieval
        self.llm = get_llm_gateway()
        self.prompt_template = self._load_prompt()

    def _load_prompt(self) -> dict:
        """Load retrieval prompt template."""
        prompt_file = Path("backend/prompts/retrieval_v1.yaml")
        with open(prompt_file) as f:
            return yaml.safe_load(f)

    def retrieve(self, query: str, top_k: int = 5) -> RetrievalDecision:
        """
        Search for relevant chunks and assess if coverage is sufficient.
        Phase 2: No retry. Phase 3 will use reformulated_query to retry if coverage is low.
        """
        # Search FAISS
        results = self.faiss.search(query, top_k=top_k)

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
            result = json.loads(response.text)
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


if __name__ == "__main__":
    # Quick test
    from src.data_loader import load_csv, create_chunks
    from src.embedding_service import EmbeddingService

    rows = load_csv("data/sample_budget_data.csv")
    chunks = create_chunks(rows)
    embedding_service = EmbeddingService()
    faiss_retrieval = FAISSRetrieval(chunks, embedding_service)

    retrieval_agent = RetrievalAgent(faiss_retrieval)

    test_queries = [
        "What was the engineering payroll variance in Q3?",
        "Which departments spent too much?",
    ]

    for query in test_queries:
        decision = retrieval_agent.retrieve(query)
        print(f"\nQuery: {query}")
        print(f"Coverage sufficient: {decision.coverage_sufficient}")
        print(f"Reasoning: {decision.reasoning}")
        if decision.reformulated_query:
            print(f"Reformulated query: {decision.reformulated_query}")
