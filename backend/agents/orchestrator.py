"""
Agent Orchestrator — State machine for the full query pipeline.
Router → Retrieval (retry once) → Drafting → Critic (revise once) → Return or Refuse
With per-agent tracing (model, latency, cost).
"""

import time
from dataclasses import dataclass
from src.retrieval import FAISSRetrieval, RetrievalResult
from backend.agents.router_agent import RouterAgent
from backend.agents.retrieval_agent import RetrievalAgent
from backend.agents.drafting_agent import DraftingAgent
from backend.agents.critic_agent import CriticAgent
from backend.models.trace import TraceRecord, AgentStepMetrics
from backend.services.trace_emitter import TraceEmitter
from backend.services.cost_calculator import calculate_cost


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
    All steps instrumented with per-agent tracing.
    """

    def __init__(self, faiss_retrieval: FAISSRetrieval, trace_emitter: TraceEmitter | None = None):
        self.faiss = faiss_retrieval
        self.router = RouterAgent()
        self.retrieval = RetrievalAgent(faiss_retrieval)
        self.drafting = DraftingAgent()
        self.critic = CriticAgent()
        self.trace_emitter = trace_emitter or TraceEmitter()

    def run(self, query: str) -> OrchestratorResult:
        """
        Run the full orchestration pipeline for a single query.
        Returns an OrchestratorResult with the answer or refusal reason.
        Emits a complete trace with per-agent metrics.
        """
        trace = TraceRecord(query=query)
        agent_path = []
        start_time = time.time()

        # Step 1: Router
        agent_path.append("router")
        router_start = time.time()
        route_decision = self.router.route(query)
        router_latency = (time.time() - router_start) * 1000

        # Record router trace
        router_model = "claude-haiku-4-5-20251001"  # Router always uses Haiku
        router_cost = calculate_cost(router_model, 200, 50)  # Estimate for router call
        trace.add_agent_step(
            AgentStepMetrics(
                agent="router",
                model=router_model,
                latency_ms=router_latency,
                input_tokens=200,
                output_tokens=50,
                cost_usd=router_cost,
            )
        )

        if not route_decision.in_scope:
            trace.agent_path = agent_path
            trace.outcome = "refused_scope"
            trace.refusal_reason = route_decision.reason
            trace.total_latency_ms = (time.time() - start_time) * 1000
            self.trace_emitter.emit(trace)

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
        retrieval_start = time.time()
        retrieval_decision = self.retrieval.retrieve(query, top_k=5)
        retrieval_latency = (time.time() - retrieval_start) * 1000

        if not retrieval_decision.coverage_sufficient and retrieval_decision.reformulated_query:
            retrieval_retried = True
            retrieval_start = time.time()
            retrieval_decision = self.retrieval.retrieve(
                retrieval_decision.reformulated_query, top_k=5
            )
            retrieval_latency += (time.time() - retrieval_start) * 1000

        # Record retrieval trace
        retrieval_model = "claude-haiku-4-5-20251001"
        retrieval_cost = calculate_cost(retrieval_model, 300, 100)  # Estimate
        trace.add_agent_step(
            AgentStepMetrics(
                agent="retrieval",
                model=retrieval_model,
                latency_ms=retrieval_latency,
                input_tokens=300,
                output_tokens=100,
                cost_usd=retrieval_cost,
            )
        )
        trace.retrieval_retried = retrieval_retried

        context = retrieval_decision.chunks

        # Step 3: Drafting
        agent_path.append("drafting")
        drafting_start = time.time()
        draft_result = self.drafting.draft(query, context)
        drafting_latency = (time.time() - drafting_start) * 1000
        current_draft = draft_result.answer

        # Record drafting trace
        drafting_model = draft_result.model_used
        trace.add_agent_step(
            AgentStepMetrics(
                agent="drafting",
                model=drafting_model,
                latency_ms=drafting_latency,
                input_tokens=draft_result.tokens_used[0],
                output_tokens=draft_result.tokens_used[1],
                cost_usd=calculate_cost(
                    drafting_model,
                    draft_result.tokens_used[0],
                    draft_result.tokens_used[1],
                ),
            )
        )

        # Step 4: Critic (can request revision once)
        agent_path.append("critic")
        draft_revised = False
        critic_start = time.time()
        critique = self.critic.review(query, current_draft, context)
        critic_latency = (time.time() - critic_start) * 1000

        # Record critic trace
        critic_model = "claude-sonnet-5"
        critic_cost = calculate_cost(critic_model, 500, 150)  # Estimate
        trace.add_agent_step(
            AgentStepMetrics(
                agent="critic",
                model=critic_model,
                latency_ms=critic_latency,
                input_tokens=500,
                output_tokens=150,
                cost_usd=critic_cost,
            )
        )

        if critique.verdict == "PASS":
            trace.agent_path = agent_path
            trace.outcome = "success"
            trace.confidence_score = critique.confidence
            trace.total_latency_ms = (time.time() - start_time) * 1000
            self.trace_emitter.emit(trace)

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
            drafting_start = time.time()
            draft_result = self.drafting.draft(query, context)
            drafting_latency = (time.time() - drafting_start) * 1000
            current_draft = draft_result.answer

            # Record revision trace (update last drafting step)
            trace.per_agent[-1] = AgentStepMetrics(
                agent="drafting",
                model=draft_result.model_used,
                latency_ms=drafting_latency,
                input_tokens=draft_result.tokens_used[0],
                output_tokens=draft_result.tokens_used[1],
                cost_usd=calculate_cost(
                    draft_result.model_used,
                    draft_result.tokens_used[0],
                    draft_result.tokens_used[1],
                ),
            )

            # Re-critique
            critic_start = time.time()
            critique = self.critic.review(query, current_draft, context)
            critic_latency = (time.time() - critic_start) * 1000

            # Update critic trace
            trace.per_agent[-1] = AgentStepMetrics(
                agent="critic",
                model="claude-sonnet-5",
                latency_ms=critic_latency,
                input_tokens=500,
                output_tokens=150,
                cost_usd=calculate_cost("claude-sonnet-5", 500, 150),
            )

            if critique.verdict == "PASS":
                trace.agent_path = agent_path
                trace.outcome = "success"
                trace.confidence_score = critique.confidence
                trace.draft_revised = True
                trace.total_latency_ms = (time.time() - start_time) * 1000
                self.trace_emitter.emit(trace)

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
        trace.agent_path = agent_path
        trace.outcome = "refused_faithfulness"
        trace.confidence_score = 0.0
        trace.draft_revised = draft_revised
        trace.refusal_reason = (
            f"Failed faithfulness review. Issues: " + ", ".join(critique.issues)
            if critique.issues else "Faithfulness check failed."
        )
        trace.total_latency_ms = (time.time() - start_time) * 1000
        self.trace_emitter.emit(trace)

        return OrchestratorResult(
            success=False,
            answer=None,
            agent_path=agent_path,
            retrieval_retried=retrieval_retried,
            draft_revised=draft_revised,
            refusal_reason=trace.refusal_reason,
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
