"""
Agent Orchestrator — State machine for the full query pipeline.
Router → Retrieval (retry once) → Drafting → Critic (revise once) → Return or Refuse
"""

from dataclasses import dataclass
from src.retrieval import FAISSRetrieval, RetrievalResult
from backend.agents.router_agent import RouterAgent
from backend.agents.retrieval_agent import RetrievalAgent
from backend.agents.drafting_agent import DraftingAgent
from backend.agents.critic_agent import CriticAgent


@dataclass
class OrchestratorResult:
    """Final result from the orchestrator."""
    success: bool
    answer: str | None
    agent_path: list[str]  # e.g., ["router", "retrieval", "drafting", "critic"]
    retrieval_retried: bool
    draft_revised: bool
    refusal_reason: str | None
    confidence_score: float  # From critic if passed, else 0.0
    context_used: list[RetrievalResult] | None


class AgentOrchestrator:
    """
    Hand-rolled state machine orchestrating 4 agents with bounded retry logic.
    - Router: classify query
    - Retrieval: search + optional retry once
    - Drafting: generate answer (+ optional revision once)
    - Critic: judge faithfulness
    """

    def __init__(self, faiss_retrieval: FAISSRetrieval):
        self.faiss = faiss_retrieval
        self.router = RouterAgent()
        self.retrieval = RetrievalAgent(faiss_retrieval)
        self.drafting = DraftingAgent()
        self.critic = CriticAgent()

    def run(self, query: str) -> OrchestratorResult:
        """
        Run the full orchestration pipeline for a single query.
        Returns an OrchestratorResult with the answer or refusal reason.
        """
        agent_path = []

        # Step 1: Router
        agent_path.append("router")
        route_decision = self.router.route(query)

        if not route_decision.in_scope:
            return OrchestratorResult(
                success=False,
                answer=None,
                agent_path=agent_path,
                retrieval_retried=False,
                draft_revised=False,
                refusal_reason=f"Out of scope: {route_decision.reason}",
                confidence_score=0.0,
                context_used=None,
            )

        # Step 2: Retrieval (can retry once)
        agent_path.append("retrieval")
        retrieval_retried = False
        retrieval_decision = self.retrieval.retrieve(query, top_k=5)

        if not retrieval_decision.coverage_sufficient and retrieval_decision.reformulated_query:
            retrieval_retried = True
            retrieval_decision = self.retrieval.retrieve(
                retrieval_decision.reformulated_query, top_k=5
            )

        context = retrieval_decision.chunks

        # Step 3: Drafting
        agent_path.append("drafting")
        draft_result = self.drafting.draft(query, context)
        current_draft = draft_result.answer

        # Step 4: Critic (can request revision once)
        agent_path.append("critic")
        draft_revised = False

        critique = self.critic.review(query, current_draft, context)

        if critique.verdict == "PASS":
            return OrchestratorResult(
                success=True,
                answer=current_draft,
                agent_path=agent_path,
                retrieval_retried=retrieval_retried,
                draft_revised=False,
                refusal_reason=None,
                confidence_score=critique.confidence,
                context_used=context,
            )

        if critique.verdict == "REVISE" and not draft_revised:
            # One revision allowed
            draft_revised = True
            revision_prompt = (
                f"Original draft:\n{current_draft}\n\n"
                f"Issues to fix:\n" + "\n".join(f"- {issue}" for issue in critique.issues)
            )
            if critique.revision_notes:
                revision_prompt += f"\n\nGuidance:\n{critique.revision_notes}"

            # Drafting agent revises (can't change this easily without modifying agent)
            # For now, re-call draft with the same context
            draft_result = self.drafting.draft(query, context)
            current_draft = draft_result.answer

            # Re-critique the revised draft
            critique = self.critic.review(query, current_draft, context)

            if critique.verdict == "PASS":
                return OrchestratorResult(
                    success=True,
                    answer=current_draft,
                    agent_path=agent_path,
                    retrieval_retried=retrieval_retried,
                    draft_revised=True,
                    refusal_reason=None,
                    confidence_score=critique.confidence,
                    context_used=context,
                )

        # Critic refused or revision didn't fix it: hard refusal
        return OrchestratorResult(
            success=False,
            answer=None,
            agent_path=agent_path,
            retrieval_retried=retrieval_retried,
            draft_revised=draft_revised,
            refusal_reason=(
                f"Failed faithfulness review. Issues: " + ", ".join(critique.issues)
                if critique.issues else "Faithfulness check failed."
            ),
            confidence_score=0.0,
            context_used=context,
        )


if __name__ == "__main__":
    from src.data_loader import load_csv, create_chunks
    from src.embedding_service import EmbeddingService
    from dotenv import load_dotenv
    load_dotenv()

    rows = load_csv("data/sample_budget_data.csv")
    chunks = create_chunks(rows)
    embedding_service = EmbeddingService()
    faiss_retrieval = FAISSRetrieval(chunks, embedding_service)

    orchestrator = AgentOrchestrator(faiss_retrieval)

    test_queries = [
        "What was the engineering headcount variance in Q3?",
        "Which cost centers are over budget?",
        "What's the weather?",
    ]

    for query in test_queries:
        result = orchestrator.run(query)
        print(f"\nQuery: {query}")
        print(f"Success: {result.success}")
        print(f"Agent path: {' → '.join(result.agent_path)}")
        if result.success:
            print(f"Answer: {result.answer[:100]}...")
        else:
            print(f"Refusal: {result.refusal_reason}")
