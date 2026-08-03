# FP&A Copilot — Architecture Document

**Version:** 2.0
**Status:** Draft
**Author:** Adedotun Adebiaye
**Last Updated:** 2026-07-28
**Changelog from v1.0:** Introduced explicit multi-agent orchestration (Router → Retrieval → Drafter → Critic), moved data access behind an MCP server, adopted tiered model routing by task risk/cost, added cost/rate guardrails for public deployment. See ADR-06 through ADR-09.

---

## 1. System Overview

FP&A Copilot is a governed, multi-agent natural language interface for finance operations data. It accepts uploaded budget/actuals datasets, answers ad hoc variance questions with source citations, and generates structured variance narratives (Commentary Mode) — with every response traced, evaluated, and auditable. Data access (retrieval, cost-center lookups, audit log reads) is exposed as MCP tools behind a dedicated server, and query handling is orchestrated across four purpose-built agents rather than a single linear pipeline.

### Design Principles

1. **Grounding over generation.** The LLM never invents financial figures. All answers are constrained to retrieved context.
2. **Evaluability by design.** Every output is structured to be independently scoreable — not just "was the answer good?" but "was this specific claim grounded?"
3. **Governance as a first-class feature.** Confidence gating, prompt versioning, model pinning, and audit logs are not afterthoughts — they are load-bearing product features.
4. **Model-agnostic and cost-tiered.** The LLM provider is an environment variable, and model selection per task is a deliberate risk/cost decision, not a single default applied everywhere.
5. **Agentic where it earns its keep.** Multi-agent structure is used where a real decision changes control flow (routing, re-querying, critique) — not applied cosmetically to a linear pipeline.

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT (Next.js)                         │
│  ┌──────────────┐  ┌──────────────────┐  ┌───────────────────┐ │
│  │  Upload UI   │  │   Q&A Chat UI    │  │  Commentary UI    │ │
│  │  (CSV/XLSX)  │  │  + Source Panel  │  │  + Review Queue   │ │
│  │              │  │  + Cost/Latency  │  │  + Cost/Latency   │ │
│  └──────┬───────┘  └────────┬─────────┘  └────────┬──────────┘ │
└─────────┼──────────────────┼────────────────────  ┼────────────┘
          │ POST /ingest      │ POST /query          │ POST /commentary
          ▼                  ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                API LAYER (FastAPI) — Rate Limited                │
│                                                                 │
│  /ingest ──► DataParser ──► ChunkBuilder ──► EmbeddingService  │
│                                                                 │
│  /query, /commentary ──► AGENT ORCHESTRATOR (hand-rolled)       │
│                                                                 │
│   ┌──────────────┐   refuse   ┌─────────────────────┐          │
│   │ Router Agent │──────────► │ Escalation Response  │          │
│   │  (Haiku)     │            └─────────────────────┘          │
│   └──────┬───────┘                                              │
│          │ in-scope                                             │
│          ▼                                                      │
│   ┌──────────────────┐   low coverage, 1x retry                 │
│   │ Retrieval Agent   │◄────────────────┐                       │
│   │  (Haiku)          │─────────────────┘                       │
│   └──────┬────────────┘                                         │
│          │ MCP call                                             │
│          ▼                                                      │
│   ┌────────────────────┐                                        │
│   │  fpa-data-mcp       │  (MCP server)                         │
│   │  search_financial_  │──► FAISS (in-memory, session-scoped)  │
│   │  data / get_cost_   │                                       │
│   │  center_rows /      │                                       │
│   │  get_audit_log      │                                       │
│   └────────────────────┘                                        │
│          │ chunks + scores                                      │
│          ▼                                                      │
│   ┌──────────────────┐                                          │
│   │ Drafting Agent    │  Haiku (Q&A) / Sonnet (Commentary)      │
│   └──────┬───────────┘                                          │
│          ▼                                                      │
│   ┌──────────────────┐   revise (max 1x)                        │
│   │ Critic Agent      │──────────┐                              │
│   │  (Sonnet)         │◄─────────┘                              │
│   └──────┬───────────┘                                          │
│          │ pass          │ fail after revise                    │
│          ▼                ▼                                     │
│   Return to user      Refuse — no partial answer,                │
│   + Langfuse trace     routed to human review queue              │
│                                                                 │
│                      TraceEmitter ──────────────────────────►  │
│                      (Langfuse SDK)                   Langfuse  │
│                                                       (Cloud)  │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────┐
│    EVAL HARNESS         │
│    (runs offline)       │
│                         │
│  GoldenDataset (25)     │
│  DeepEval GEval         │
│  Sonnet-as-Judge        │
│  EvalRunner             │
│  ReportExporter         │
└─────────────────────────┘
```

---

## 3. Component Breakdown

### 3.1 Frontend — Next.js (App Router)

**Why Next.js:** Server components for the governance sidebar (rendered server-side, no client JS needed for static trace data). Client components for the chat interface and inline editing. Single repo, deployable as a container.

**Key pages:**
- `/` — Upload + session initialization
- `/query` — Q&A chat interface with source panel
- `/commentary` — Commentary Mode with review queue and export
- `/audit` — Session audit log viewer (JSON export, filterable by trace type / escalation status)

**Governance sidebar (every response):**
- Model name + version, per agent step (Router / Retrieval / Drafter / Critic may use different models)
- Prompt template version
- Confidence score (visual indicator: green ≥ 0.8, amber 0.6–0.8, red < 0.6)
- Retrieved chunk IDs with row references
- Which agent path was taken (straight-through / retried retrieval / revised draft / refused)
- Estimated cost (tokens in/out × per-model rate) and latency, broken down by agent step
- Langfuse trace link

Batch (non-streaming) responses for both Q&A and Commentary Mode: since the Critic Agent can refuse a draft outright, streaming a response that might then be withheld creates confusing UX. Both modes wait for the full agent loop to complete before rendering.

### 3.2 API Layer — FastAPI (Python)

**`/ingest`** — unchanged from v1: `DataParser` → `ChunkBuilder` → `EmbeddingService` → session-scoped FAISS index, now accessed exclusively through the MCP server rather than directly by application code.

**`/query` and `/commentary`** now both route through a single `AgentOrchestrator` rather than separate linear handlers:

```python
class AgentOrchestrator:
    """Hand-rolled state machine. No external graph framework —
    4 agents and a bounded 2-iteration loop don't warrant one."""

    async def run(self, session_id: str, query: str, mode: Mode) -> OrchestratorResult:
        route = await self.router.classify(query, mode)
        if route.out_of_scope:
            return OrchestratorResult.refused(route.reason)

        retrieval = await self.retrieval_agent.fetch(session_id, query)
        if retrieval.coverage_low and not retrieval.already_retried:
            retrieval = await self.retrieval_agent.fetch(
                session_id, retrieval.reformulated_query, retry=True
            )

        draft = await self.drafting_agent.generate(query, retrieval.chunks, mode)
        critique = await self.critic_agent.review(draft, retrieval.chunks)

        if critique.passed:
            return OrchestratorResult.success(draft, critique, retrieval)

        if not critique.already_revised:
            draft = await self.drafting_agent.generate(
                query, retrieval.chunks, mode, revision_notes=critique.notes
            )
            critique = await self.critic_agent.review(draft, retrieval.chunks)
            if critique.passed:
                return OrchestratorResult.success(draft, critique, retrieval)

        return OrchestratorResult.refused(
            "Failed faithfulness review after one revision.",
            route_to_human_review=True
        )
```

**Agent responsibilities:**

| Agent | Model | Decision it makes | Failure mode handling |
|---|---|---|---|
| Router | Haiku 4.5 | In-scope Q&A / Commentary / out-of-scope | Refuse with reason, no LLM call downstream |
| Retrieval | Haiku 4.5 | Sufficient context, or reformulate + retry once | After 1 retry, proceeds with best-available context, flagged in trace |
| Drafter | Haiku 4.5 (Q&A) / Sonnet 5 (Commentary) | Generates answer/narrative from context | N/A — generation only |
| Critic | Sonnet 5 (deliberately different from Q&A drafter to reduce same-model bias) | Pass / request one revision / refuse | On refuse: no partial output shown to user, routed to human review queue |

**`/commentary` response format:** unchanged structured JSON `{summary, primary_driver, secondary_drivers, outlook, confidence}`, now produced and verified through the same orchestrator rather than a separate `CommentaryOrchestrator` class — Q&A and Commentary Mode differ only in prompt template and drafting model, not in control flow.

### 3.3 MCP Server — `fpa-data-mcp`

**Decision: data access is exposed as an MCP server, not called in-process.**

```
fpa-data-mcp/
├── server.py
└── tools/
    ├── search_financial_data.py   # query, session_id, top_k -> chunks + scores
    ├── get_cost_center_rows.py    # cost_center, session_id, period -> rows
    └── get_audit_log.py           # session_id -> trace records
```

Why this boundary and not others: these are the three places the system talks to *data* rather than to the *LLM*. Wrapping LLM calls themselves in MCP would be unusual; wrapping data access is the standard pattern and gives the retrieval layer a real service boundary — in a real institution, this is the piece a second team (e.g., a separate reporting agent) would plausibly want to call too.

**Trade-off accepted:** an extra network hop and serialization overhead per retrieval call, versus a direct FAISS library call. For a single-session, single-instance v1 deployment this is a deliberate cost paid for architectural honesty about the service boundary, not a performance requirement.

### 3.4 Data Layer — Session-Scoped, In-Memory (v1)

**Decision: No persistent database in v1.** Unchanged rationale from v1.0: eliminates data residency risk, auth complexity, and operational overhead.

**Known limitation, stated explicitly:** because FAISS lives in-process behind the MCP server, this only works correctly with **exactly one backend replica**. Azure Container Apps scale-to-zero is fine (cold start just means session loss, already accepted), but if the app is ever configured to scale to >1 replica, sessions will inconsistently 404 depending on which replica serves the request. v1 pins `minReplicas=0, maxReplicas=1` for this reason — this is a constraint, not an oversight. v2 introduces Redis for session state and pgvector/Azure AI Search for the vector index specifically to remove this constraint.

### 3.5 LLM Gateway — Model-Agnostic, Tiered by Task

All LLM calls still route through the `LLMGateway` interface from v1.0 — that abstraction is unchanged and remains the most important piece of the system. What's new is that **model selection is now a per-agent configuration, not a single pinned model for the whole app.**

```python
class LLMGateway(ABC):
    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system: str,
        response_format: ResponseFormat,
        max_tokens: int,
        temperature: float,
        model_override: str | None = None,  # NEW: per-agent model selection
    ) -> LLMResponse:
        ...

class AnthropicAdapter(LLMGateway):
    DEFAULT_MODELS = {
        "router": "claude-haiku-4-5-20251001",
        "retrieval": "claude-haiku-4-5-20251001",
        "drafter_qa": "claude-haiku-4-5-20251001",
        "drafter_commentary": "claude-sonnet-5",
        "critic": "claude-sonnet-5",
    }

class AzureOpenAIAdapter(LLMGateway):
    DEFAULT_MODELS = {
        "router": "gpt-4o-mini",
        "retrieval": "gpt-4o-mini",
        "drafter_qa": "gpt-4o-mini",
        "drafter_commentary": "gpt-4o",
        "critic": "gpt-4o",
    }
```

**Why tiered instead of one pinned model:** routing and scope classification don't need frontier reasoning — a cheap, fast model is not just cost-effective but *more* appropriate (lower latency for a task that gates every request). Commentary narratives feed a CFO deck and warrant the stronger model. The Critic deliberately uses a different, generally-stronger model than the Q&A Drafter to reduce the same-model-grading-itself bias that v1.0 flagged but didn't fully address — full separation (a third-party judge model) remains a v2 item, noted in §6.3.

**Provider selection:** `LLM_PROVIDER=anthropic|azure_openai`, unchanged. Per-agent model within a provider is configurable via the `DEFAULT_MODELS` map, overridable by environment variable for eval comparisons (e.g., "does Sonnet as Q&A drafter meaningfully beat Haiku on this golden dataset, or is Haiku good enough?" — this is itself a question the eval harness should answer before assuming Haiku is sufficient).

**Model pinning:** unchanged — exact versions logged with every trace, no `latest` aliases.

### 3.6 Observability — Langfuse

Trace schema extended from v1.0 to capture per-agent detail:

```json
{
  "trace_id": "uuid",
  "session_id": "uuid",
  "trace_type": "qa | commentary",
  "timestamp": "ISO-8601",
  "query": "string",
  "agent_path": ["router", "retrieval", "drafter", "critic"],
  "retrieval_retried": false,
  "draft_revised": false,
  "outcome": "success | refused_scope | refused_faithfulness",
  "per_agent": [
    {"agent": "router", "model": "claude-haiku-4-5-20251001", "latency_ms": 210, "cost_usd": 0.0004},
    {"agent": "retrieval", "model": "claude-haiku-4-5-20251001", "latency_ms": 340, "cost_usd": 0.0006},
    {"agent": "drafter", "model": "claude-sonnet-5", "latency_ms": 1800, "cost_usd": 0.011},
    {"agent": "critic", "model": "claude-sonnet-5", "latency_ms": 1400, "cost_usd": 0.009}
  ],
  "confidence_score": 0.0,
  "eval_scores": {
    "faithfulness": 0.0,
    "answer_relevance": 0.0,
    "contextual_precision": 0.0
  },
  "total_cost_usd": 0.021,
  "total_latency_ms": 3750,
  "escalated": false
}
```

**What this adds over v1.0:** per-agent cost and latency breakdown, so the governance sidebar's cost indicator (§3.1) and the "is Haiku good enough for the Q&A drafter" eval question both have real data to point at, instead of a single opaque per-response number.

---

## 4. Cost & Rate Guardrails (New — v2.0)

Because this is deployed publicly and cost-consciousness was an explicit goal, the following are treated as governance features, on par with confidence gating:

- **Per-session query cap:** configurable, default 50 queries/session, enforced at the orchestrator entry point before any agent runs.
- **Per-IP rate limit:** sliding window, default 20 requests/minute, enforced at the FastAPI middleware layer (before `/ingest`, `/query`, `/commentary`).
- **Daily cost ceiling:** a running total (from the trace store) checked before each new agent run; once exceeded, new requests return a clear "temporarily unavailable" response rather than silently failing or draining the API budget.
- **Router-first cost containment:** because the Router Agent always runs first and uses the cheapest model, out-of-scope or abusive queries are rejected before any retrieval or drafting cost is incurred — this is a secondary benefit of the routing decision beyond scope classification.

These are documented as portfolio-appropriate controls, not enterprise-grade rate limiting — no Redis-backed distributed limiter in v1, in-process counters are sufficient given the single-replica constraint in §3.4.

---

## 5. Key Architectural Decisions (ADRs)

### ADR-01: In-memory vector store (FAISS) vs. managed vector DB
*(unchanged from v1.0 — see §3.4 for the added replica-count constraint)*
**Decision:** FAISS in-process for v1, now accessed via MCP rather than directly.
**Trade-off accepted:** Sessions lost on restart; single-replica-only deployment.

### ADR-02: Structured JSON for Commentary Mode output
*(unchanged from v1.0)*
**Decision:** LLM returns structured JSON; frontend renders as markdown.

### ADR-03: Model-agnostic gateway with environment-variable switching
*(unchanged from v1.0, extended by ADR-07 below)*
**Decision:** Abstract LLM provider behind interface; switch via env var.

### ADR-04: Confidence scoring via secondary LLM call vs. heuristic
*(unchanged from v1.0)*
**Decision:** Secondary LLM call (Critic Agent, Sonnet 5) for faithfulness in the request path; lightweight heuristic for real-time UI confidence display.
**Note added in v2.0:** heuristic weights (§7) are starting values, not calibrated against the golden dataset yet — this is an open item, not a finished result.

### ADR-05: FastAPI (Python) vs. Next.js API routes
*(unchanged from v1.0)*

### ADR-06: Data access behind an MCP server, not direct library calls
**Decision:** Retrieval, cost-center lookup, and audit log reads are exposed as MCP tools via `fpa-data-mcp`, consumed by agents as an MCP client rather than imported directly.
**Alternatives considered:** Direct FAISS/session-store calls from agent code (simpler, lower latency).
**Rationale:** Establishes a real service boundary for data access — the piece most likely to be shared across future agents or teams in a real institution. Demonstrates MCP as a genuine architectural pattern rather than a superficial integration.
**Trade-off accepted:** Added network hop and serialization overhead per retrieval call, for a single-process v1 deployment where it isn't strictly required. Accepted as a deliberate demonstration of the pattern, documented as such rather than presented as a performance-motivated choice.

### ADR-07: Tiered model selection by agent role, not a single pinned model
**Decision:** Router, Retrieval, and Q&A Drafting agents default to Haiku 4.5 / gpt-4o-mini; Commentary Drafting and the Critic Agent default to Sonnet 5 / gpt-4o.
**Alternatives considered:** Single model for all calls (v1.0's approach); always use the cheapest model everywhere; always use the strongest model everywhere.
**Rationale:** Cost and latency should scale with task risk, not be uniform. Classification and routing don't need frontier reasoning. Commentary narratives are higher-stakes (feed CFO decks) and warrant the stronger model. Using a different, generally-stronger model for the Critic than the Q&A Drafter partially addresses the same-model-judging-itself bias.
**Trade-off accepted:** More configuration surface (per-agent model maps instead of one constant); eval harness must validate that Haiku is actually sufficient for Q&A drafting rather than assuming it — this validation is itself part of the v1 eval plan (§6.4).

### ADR-08: Hand-rolled orchestrator vs. agent framework (LangGraph)
**Decision:** A ~150-line hand-rolled async state machine (`AgentOrchestrator`), no LangGraph or similar dependency.
**Alternatives considered:** LangGraph (more standard/recognizable in job postings), CrewAI, AutoGen.
**Rationale:** Four agents with a bounded 2-iteration loop (one retrieval retry, one draft revision) is simple enough to implement and explain directly. A framework adds a dependency and a layer of abstraction that isn't earning its complexity budget at this scale, and "I understand exactly what my orchestration code does because I wrote it" is a stronger interview answer than "I configured a graph library."
**Trade-off accepted:** Less resume-recognizable than naming a specific framework; if the agent graph grows materially (more agents, more branching, parallel agent calls), this would need to be revisited — noted as a v2 trigger condition, not deferred silently.

### ADR-09: Cost/rate guardrails treated as governance features
**Decision:** Per-session query caps, per-IP rate limiting, and a daily cost ceiling are implemented at the API layer and documented in the architecture, not left as an operational afterthought.
**Rationale:** A public, cost-conscious portfolio deployment without spend controls is a real operational risk, not just a nice-to-have. Framing these alongside confidence gating and audit logging keeps "governance" honest — it covers cost and abuse, not only model output quality.
**Trade-off accepted:** In-process counters only (no distributed rate limiter), acceptable given the single-replica constraint from ADR-01/§3.4.

---

## 6. Confidence Scoring (Real-Time Heuristic)

Unchanged from v1.0 — composite of retrieval similarity (0.40), retrieval coverage (0.20), hedge detection (0.20), response length vs. complexity (0.10), scope pre-check pass (0.10). **Explicitly noted as uncalibrated starting weights** (see ADR-04); calibration against the golden dataset is an open v1 task, not a completed one.

- ≥ 0.80 → High confidence (green)
- 0.60–0.79 → Medium confidence (amber)
- < 0.60 → Escalate — handled by the Critic Agent's refusal path, not a separate mechanism

---

## 7. Eval Design

### 7.1 Golden Dataset (25 cases)

Same five categories as v1.0 (direct lookup, variance calc, multi-row aggregation, out-of-scope refusal, commentary quality). **Stated explicitly:** 25 cases gives a per-case granularity of 4% on the hallucination-rate goal — illustrative for a portfolio project, not statistically rigorous. Expanding the dataset is a documented v1.1 task if time allows, not claimed as complete now.

### 7.2 Metrics (DeepEval GEval)

Unchanged categories from v1.0: Faithfulness, Answer Relevance, Contextual Precision, Hallucination, Refusal Accuracy, Commentary Faithfulness (per field).

**New in v2.0 — Model tier comparison:** the eval harness runs the Q&A path with both Haiku-as-drafter and Sonnet-as-drafter configurations and reports faithfulness/relevance deltas alongside cost deltas. This directly answers ADR-07's open question rather than assuming the cheaper model is adequate.

### 7.3 Judge Model

**Decision, revised from v1.0:** the eval harness judge uses Sonnet 5. Where the Drafting Agent under test is also Sonnet 5 (Commentary path), this remains a same-model-judging-itself risk, disclosed as in v1.0. Where the Drafting Agent under test is Haiku (Q&A path), the judge is now a different, stronger model than the one being evaluated — a partial improvement over v1.0's setup, not a full fix (a fully independent third-party judge model remains a v2 item).

### 7.4 Eval Runner

```bash
python eval/run_eval.py --dataset data/golden_dataset.json --provider anthropic
python eval/run_eval.py --dataset data/golden_dataset.json --provider azure_openai
python eval/compare_providers.py --dataset data/golden_dataset.json
python eval/compare_model_tiers.py --dataset data/golden_dataset.json  # NEW
```

Output: `eval/reports/eval_report_{timestamp}.json` + console summary table, now including per-agent cost totals.

---

## 8. Deployment

### 8.1 Decision: Azure Container Apps (primary), AWS App Runner (secondary, proves portability)

**Decision:** Azure Container Apps remains the primary deployment target, for the reasons in v1.0 (Azure OpenAI integration story, bank hiring signal). **New in v2.0:** a secondary AWS App Runner deployment, using a third `LLMGateway` adapter (`BedrockAdapter`), is a stated v1 stretch goal rather than a v2 deferral — it directly demonstrates that the model-agnostic abstraction actually works across clouds, not just across two API vendors on the same cloud. If time doesn't allow both, Azure ships first and AWS is documented as the next increment, not silently dropped.

### 8.2 Container Architecture

```
docker-compose.yml (local dev)
├── frontend (Next.js, port 3000)
├── backend (FastAPI, port 8000)
├── mcp-server (fpa-data-mcp, port 8100)
└── (no DB container — session-scoped in-memory)

Azure Container Apps (production)
├── fpa-copilot-frontend      (Container App)
├── fpa-copilot-backend       (Container App, minReplicas=0, maxReplicas=1 — see §3.4)
├── fpa-copilot-mcp-server    (Container App, same replica constraint)
└── Azure Container Registry (image storage)
```

### 8.3 Environment Variables

```bash
# Backend
LLM_PROVIDER=anthropic | azure_openai
ANTHROPIC_API_KEY=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
MCP_SERVER_URL=http://fpa-data-mcp:8100
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
CONFIDENCE_THRESHOLD=0.60
COMMENTARY_FAITH_THRESHOLD=0.75
MAX_QUERIES_PER_SESSION=50
RATE_LIMIT_PER_IP_PER_MIN=20
DAILY_COST_CEILING_USD=10.00

# Frontend
NEXT_PUBLIC_API_URL=https://fpa-copilot-backend.azurecontainerapps.io
```

### 8.4 CI/CD (GitHub Actions)

```
.github/workflows/
├── eval.yml        # Run eval harness on PR (fails PR if faithfulness < 0.80)
├── model_tier.yml  # Run eval on both Haiku and Sonnet drafter configs, post cost/quality delta as PR comment
├── build.yml       # Build and push Docker images to ACR
└── deploy.yml      # Deploy to Azure Container Apps on main branch merge
```

---

## 9. Repository Structure

```
fpa-copilot/
├── README.md
├── ARCHITECTURE.md
├── PRD.md
├── docker-compose.yml
├── .github/workflows/
│
├── frontend/                    # Next.js app
│   ├── app/
│   │   ├── page.tsx
│   │   ├── query/page.tsx
│   │   ├── commentary/page.tsx
│   │   └── audit/page.tsx
│   └── components/
│       ├── GovernanceSidebar.tsx   # now shows per-agent path + cost
│       ├── SourcePanel.tsx
│       └── ReviewQueue.tsx
│
├── backend/                     # FastAPI app
│   ├── main.py
│   ├── routers/
│   │   ├── ingest.py
│   │   ├── query.py
│   │   └── commentary.py
│   ├── agents/                  # NEW
│   │   ├── orchestrator.py      # AgentOrchestrator state machine
│   │   ├── router_agent.py
│   │   ├── retrieval_agent.py
│   │   ├── drafting_agent.py
│   │   └── critic_agent.py
│   ├── services/
│   │   ├── llm_gateway.py       # abstract base + adapters, tiered model config
│   │   ├── mcp_client.py        # NEW — client for fpa-data-mcp
│   │   ├── confidence.py
│   │   ├── rate_limit.py        # NEW — cost/rate guardrails
│   │   └── trace.py
│   └── prompts/
│       ├── router_v1.yaml
│       ├── retrieval_v1.yaml
│       ├── qa_drafter_v1.yaml
│       ├── commentary_drafter_v1.yaml
│       └── critic_v1.yaml
│
├── mcp-server/                  # NEW — fpa-data-mcp
│   ├── server.py
│   └── tools/
│       ├── search_financial_data.py
│       ├── get_cost_center_rows.py
│       └── get_audit_log.py
│
├── eval/
│   ├── run_eval.py
│   ├── compare_providers.py
│   ├── compare_model_tiers.py   # NEW
│   ├── metrics/
│   │   ├── faithfulness.py
│   │   ├── hallucination.py
│   │   └── refusal_accuracy.py
│   └── data/
│       └── golden_dataset.json
│
└── infra/
    ├── containerapp-backend.yaml
    ├── containerapp-mcp-server.yaml
    ├── containerapp-frontend.yaml
    └── deploy.sh
```

---

## 10. What This Architecture Demonstrates

**For a Finance & Business Management VP/Director role:**
- Deep enough FP&A workflow understanding to build tooling for it
- Scope decisions (no live ERP, session-scoped data, single-replica constraint) that reflect real institutional constraints, stated rather than hidden
- SR 11-7-aligned governance built in from the start, extended to cover cost/abuse controls, not only output quality

**For a Model Risk Governance & Review role:**
- Confidence gating, a critic agent with a hard refusal path, and audit logs as first-class requirements
- Explicit disclosure of uncalibrated heuristic weights and same-model judge bias, rather than presenting either as more rigorous than it is
- Model version pinning and prompt versioning, now per-agent

**For an AI PM / applied AI role:**
- Real architectural decisions (ADR-01 through ADR-09) with explicit trade-offs, including two decisions (MCP boundary, orchestration framework) chosen *against* the more resume-recognizable option, with reasoning stated
- A multi-agent design where each agent earns its place via an actual control-flow decision, not agent-shaped naming over a linear pipeline
- Tiered model selection as a cost/risk product decision, validated by the eval harness rather than assumed
