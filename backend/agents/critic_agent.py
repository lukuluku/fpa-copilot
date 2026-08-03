"""
Critic Agent — Judge faithfulness of drafts to retrieved context.
Can pass, request revision, or refuse.
"""

import json
import yaml
from pathlib import Path
from dataclasses import dataclass
from src.retrieval import RetrievalResult
from backend.services.llm_gateway import get_llm_gateway


@dataclass
class CriticDecision:
    """Decision from the Critic Agent."""
    verdict: str  # "PASS" | "REVISE" | "REFUSE"
    confidence: float
    issues: list[str]
    revision_notes: str | None


class CriticAgent:
    """Critic Agent: judge faithfulness of drafts."""

    def __init__(self):
        self.llm = get_llm_gateway()
        self.prompt_template = self._load_prompt()

    def _load_prompt(self) -> dict:
        """Load critic prompt template."""
        prompt_file = Path("backend/prompts/critic_v1.yaml")
        with open(prompt_file) as f:
            return yaml.safe_load(f)

    def review(
        self, query: str, draft: str, context: list[RetrievalResult]
    ) -> CriticDecision:
        """
        Review a draft for faithfulness to the retrieved context.
        Returns a CriticDecision: PASS, REVISE, or REFUSE.
        """
        # Format context
        context_text = "\n".join(
            [
                f"[{chunk.chunk.chunk_id}] (score: {chunk.score:.3f})\n{chunk.chunk.text}"
                for chunk in context
            ]
        )

        system = self.prompt_template["system"]
        user_template = self.prompt_template["user_template"]
        user = user_template.format(query=query, draft=draft, context=context_text)

        response = self.llm.sync_complete(
            system=system,
            user=user,
            temperature=0.0,  # Deterministic critique
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
            return CriticDecision(
                verdict=result.get("verdict", "REFUSE").upper(),
                confidence=result.get("confidence", 0.0),
                issues=result.get("issues", []),
                revision_notes=result.get("revision_notes"),
            )
        except json.JSONDecodeError:
            # Fallback: refuse if parsing fails
            return CriticDecision(
                verdict="REFUSE",
                confidence=0.0,
                issues=[f"Failed to parse critic response: {response.text}"],
                revision_notes=None,
            )


if __name__ == "__main__":
    from src.data_loader import load_csv, create_chunks
    from src.embedding_service import EmbeddingService
    from src.retrieval import FAISSRetrieval

    rows = load_csv("data/sample_budget_data.csv")
    chunks = create_chunks(rows)
    embedding_service = EmbeddingService()
    faiss_retrieval = FAISSRetrieval(chunks, embedding_service)

    query = "What was the engineering headcount variance?"
    context = faiss_retrieval.search(query, top_k=3)

    draft = (
        "Engineering headcount was -5.6% unfavorable, spending $475k vs. $450k budget.\n"
        "This represents a $25k overage in Q3 2026."
    )

    critic = CriticAgent()
    decision = critic.review(query, draft, context)

    print(f"Query: {query}")
    print(f"Verdict: {decision.verdict}")
    print(f"Confidence: {decision.confidence}")
    if decision.issues:
        print(f"Issues: {decision.issues}")
    if decision.revision_notes:
        print(f"Revision notes: {decision.revision_notes}")
