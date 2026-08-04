"""
Drafting Agent — Generate answers grounded in retrieved context.
"""

import os
import yaml
from pathlib import Path
from dataclasses import dataclass
from src.retrieval import RetrievalResult
from backend.services.llm_gateway import get_llm_gateway


@dataclass
class DraftingResult:
    """Result from the Drafting Agent."""
    answer: str
    context_used: list[RetrievalResult]
    model_used: str
    tokens_used: tuple[int, int]  # (input, output)


class DraftingAgent:
    """Drafting Agent: generate answers from retrieved context."""

    def __init__(self):
        self.llm = get_llm_gateway()
        self.prompt_template = self._load_prompt()

    def _load_prompt(self) -> dict:
        """Load drafting prompt template."""
        prompt_file = Path("backend/prompts/qa_drafter_v1.yaml")
        with open(prompt_file) as f:
            return yaml.safe_load(f)

    def draft(self, query: str, context: list[RetrievalResult]) -> DraftingResult:
        """
        Generate an answer grounded in the provided context chunks.
        Respects EVAL_USE_SONNET env var for testing (Phase 6 comparison).
        """
        # Format context for the prompt
        context_text = "\n".join(
            [
                f"[{chunk.chunk.chunk_id}] (score: {chunk.score:.3f})\n{chunk.chunk.text}"
                for chunk in context
            ]
        )

        system = self.prompt_template["system"]
        user_template = self.prompt_template["user_template"]
        user = user_template.format(query=query, context=context_text)

        # Allow override to Sonnet for testing (Phase 6 A/B test)
        model_override = None
        if os.getenv("EVAL_USE_SONNET"):
            model_override = "claude-sonnet-5"

        response = self.llm.sync_complete(
            system=system,
            user=user,
            temperature=0.7,  # Slight creativity for natural language
            max_tokens=1024,
            model_override=model_override,
        )

        return DraftingResult(
            answer=response.text,
            context_used=context,
            model_used=response.model,
            tokens_used=(response.input_tokens, response.output_tokens),
        )


if __name__ == "__main__":
    # Quick test
    from src.data_loader import load_csv, create_chunks
    from src.embedding_service import EmbeddingService
    from src.retrieval import FAISSRetrieval

    rows = load_csv("data/sample_budget_data.csv")
    chunks = create_chunks(rows)
    embedding_service = EmbeddingService()
    faiss_retrieval = FAISSRetrieval(chunks, embedding_service)

    query = "What was the engineering payroll variance in Q3?"
    context = faiss_retrieval.search(query, top_k=3)

    drafter = DraftingAgent()
    result = drafter.draft(query, context)

    print(f"Query: {query}")
    print(f"\nAnswer:\n{result.answer}")
    print(f"\nModel: {result.model_used}")
    print(f"Tokens: {result.tokens_used[0]} input, {result.tokens_used[1]} output")
