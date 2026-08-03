# Product Requirements Document
## FP&A Copilot with Commentary Mode

**Version:** 2.0
**Status:** Draft
**Author:** Adedotun Adebiaye
**Last Updated:** 2026-07-28
**Reviewers:** TBD
**Changelog from v1.0:** Added multi-agent orchestration (Router/Retrieval/Drafter/Critic), MCP-based data access, tiered model requirements, and cost/rate guardrails as explicit goals. See §6.6, §6.7, and updated §2 metrics.

---

## 1. Problem Statement

*(Unchanged from v1.0)*

Finance operations teams at large institutions spend disproportionate time on two low-leverage tasks:

1. **Answering ad hoc variance questions** — analysts manually query GL systems, cross-reference budget files, and compose answers in email or chat. This is slow, inconsistent, and undocumented.
2. **Writing variance commentary** — every close cycle, FP&A managers draft narratives explaining budget vs. actuals for CFO decks and board reports. This is repetitive, high-stakes, and bottlenecked on senior staff.

LLM-powered tools exist for general Q&A, but they are not built for the regulated finance context: they hallucinate, they lack source citations, they have no confidence gating, and they produce no audit trail. Deploying them in a finance operations setting without governance guardrails is a model risk violation under SR 11-7.

**FP&A Copilot** closes this gap: a governed, grounded, multi-agent NL interface for finance operations data — with an integrated Commentary Mode that produces reviewable variance narratives from the same underlying agent pipeline, at a cost profile appropriate to each task's risk.

---

## 2. Goals

| Goal | Metric | Target |
|------|--------|--------|
| Accurate Q&A grounded in source data | Faithfulness score (GEval) | ≥ 0.85 on golden dataset |
| Low hallucination rate | Hallucination eval (GEval) | ≤ 5% of responses flagged (25-case dataset — see Open Question OQ-05 on statistical granularity) |
| Commentary Mode adoption | % of queries using Commentary Mode | ≥ 30% of sessions |
| Governance coverage | % of responses with full trace logged, per-agent | 100% |
| Escalation accuracy | Human review queue precision | ≥ 90% (low-confidence answers correctly flagged) |
| Time-to-answer | P95 response latency, full agent loop | ≤ 8 seconds |
| **Cost efficiency (new)** | Average cost per successful response | Reported and tracked; Haiku-tier agents must show ≥ 60% cost reduction vs. all-Sonnet baseline on Router/Retrieval/Q&A-drafting, with no material faithfulness regression (validated by eval, not assumed) |
| **Cost containment (new)** | Daily spend stays within configured ceiling | 100% of days, enforced automatically, not monitored manually |

---

## 3. Non-Goals (v1.0, carried forward)

- **No live ERP/GL integration.** v1 uses uploaded CSV/Excel datasets. Live connectors (SAP, Oracle, Workday) are v2.
- **No multi-tenant auth.** Single-user deployment for portfolio demonstration. Auth hardening is a v2 concern. (Rate limiting and session/cost caps — §6.7 — are v1, but these are abuse/cost controls, not authentication.)
- **No chart generation.** Text-grounded answers only. Visualization is a v2 feature.
- **No fine-tuning.** Prompt engineering + retrieval grounding only.
- **No real financial data.** All datasets used in development and demo are synthetic or public-domain.
- **No distributed multi-replica deployment.** v1 is pinned to a single backend/MCP replica due to the in-memory FAISS design (see Architecture §3.4). Horizontal scaling is a v2 item requiring Redis/pgvector.
- **No agent framework dependency (LangGraph, CrewAI, etc.).** The orchestrator is hand-rolled by design (Architecture ADR-08); adopting a framework is a documented v2 trigger if the agent graph grows materially, not a v1 gap.

---

## 4. Users

*(Unchanged from v1.0)*

### Primary User: Finance Analyst
Works in FP&A, Finance Operations, or Business Management. Spends significant time answering "why is X over/under budget" questions. Comfortable with Excel; not a technical user. Needs fast, accurate answers with clear sourcing.

### Secondary User: FP&A Manager / Controller
Owns the close cycle and variance commentary deliverable. Reviews and approves analyst outputs before they reach the CFO. Needs a human review queue, confidence transparency, exportable output.

### Observed User: Model Risk / Internal Audit
Needs full prompt logs, model version pinning per agent step, confidence scores, decision rationale, and — new in v2.0 — visibility into which agent path a given response took (straight-through, retried, revised, or refused).

---

## 5. User Stories

### Q&A Mode
- **US-01:** As a finance analyst, I can upload a budget vs. actuals CSV so that I can query it in natural language without writing SQL.
- **US-02:** As a finance analyst, I can ask "Which cost centers are over budget by more than 10%?" and receive a grounded, cited answer within 8 seconds.
- **US-03:** As a finance analyst, I can see which rows of the source data the answer was drawn from, so I can verify it.
- **US-04:** As a finance analyst, I receive a clear message when the system cannot answer confidently, rather than a hallucinated response.
- **US-04a (new):** As a finance analyst, if my first query is too broad or ambiguous for the retriever to find strong matches, the system automatically reformulates and retries once before either answering or refusing — I don't have to notice a bad answer and manually re-ask.

### Commentary Mode
- **US-05:** As an FP&A manager, I can select a cost center and trigger Commentary Mode to generate a draft variance narrative.
- **US-06:** As an FP&A manager, I can see the confidence score and source citations for each claim in the narrative.
- **US-07:** As an FP&A manager, I can edit the draft inline and export it as plain text or markdown for use in a CFO deck.
- **US-08:** As an FP&A manager, low-confidence drafts are automatically flagged and routed to a human review queue.
- **US-08a (new):** As an FP&A manager, if a draft narrative fails the faithfulness check even after one automatic revision attempt, I see a clear refusal — never a partial or unverified narrative — so nothing ungrounded can accidentally make it into a deck.

### Governance
- **US-09:** As a model risk reviewer, I can export a full audit log of all queries, retrieved context chunks, model responses, and eval scores for any session.
- **US-10:** As a model risk reviewer, I can see which model version and prompt version was used for each response — and, new in v2.0, for each individual agent step within that response (routing, retrieval, drafting, critique may each use a different model).
- **US-11 (new):** As a model risk reviewer, I can see the agent path a response took (straight-through vs. retried retrieval vs. revised draft vs. refused) so I can distinguish "the system answered confidently on the first pass" from "the system had to work for this one."

### Cost & Operations (new)
- **US-12:** As the product owner, I can see per-response and daily aggregate cost, broken down by agent, so I know where spend is going.
- **US-13:** As the product owner, a single user or automated script cannot exhaust my API budget — per-session query caps and per-IP rate limits are enforced automatically.

---

## 6. Functional Requirements

### 6.1 Data Ingestion
*(Unchanged from v1.0)*
- **FR-01:** System SHALL accept CSV and Excel (.xlsx) uploads up to 10MB.
- **FR-02:** System SHALL parse and validate column headers on upload, flagging ambiguous or missing fields.
- **FR-03:** System SHALL store uploaded data in session-scoped state only (no persistence to external DB in v1).

### 6.2 Agent Orchestration (revised from v1.0's "Q&A Pipeline")
- **FR-04:** System SHALL route every query through a Router Agent that classifies it as in-scope Q&A, in-scope Commentary, or out-of-scope before any retrieval or generation occurs.
- **FR-05:** System SHALL use a Retrieval Agent that fetches the top-k relevant chunks via the MCP server (§6.5) and MAY reformulate and retry the query exactly once if retrieved context coverage is low.
- **FR-06:** System SHALL construct a grounded prompt using retrieved context only — no reliance on model parametric knowledge for financial figures.
- **FR-07:** System SHALL use a Drafting Agent to generate the answer or narrative from retrieved context, using a model appropriate to the task's risk tier (§6.6).
- **FR-08:** System SHALL use a Critic Agent, using a model distinct from the Drafting Agent where feasible, to review each draft for faithfulness against retrieved context before it is returned to the user.
- **FR-09:** System SHALL allow the Critic Agent to request exactly one revision from the Drafting Agent if the initial draft fails review.
- **FR-10:** System SHALL refuse to return a response — showing no partial or unverified output — if a draft fails Critic Agent review after one revision attempt, and SHALL route it to the human review queue.
- **FR-11:** System SHALL display a confidence score (0.0–1.0) with every returned response.
- **FR-12:** System SHALL display source citations (row references or chunk IDs) alongside every answer.

### 6.3 Commentary Mode
- **FR-13:** System SHALL accept a cost center or budget line selection as Commentary Mode input.
- **FR-14:** System SHALL generate a structured variance narrative via the same agent orchestration as Q&A (§6.2): summary sentence, primary driver, secondary drivers, outlook.
- **FR-15:** System SHALL allow inline editing of the draft narrative before export.

### 6.4 Observability
- **FR-16:** System SHALL emit a structured trace to Langfuse for every query, including a per-agent breakdown: which agents ran, which model each used, latency and cost per agent, and the overall agent path taken (straight-through / retried / revised / refused).
- **FR-17:** System SHALL log model name, model version, and prompt template version for each individual agent step, not only for the response as a whole.
- **FR-18:** System SHALL support audit log export as JSON for any session, filterable by trace type and escalation status.

### 6.5 MCP Data Access Layer (new)
- **FR-19:** System SHALL expose retrieval (`search_financial_data`), cost-center row lookup (`get_cost_center_rows`), and audit log access (`get_audit_log`) as MCP tools served by a dedicated `fpa-data-mcp` server, consumed by agents as an MCP client rather than via direct in-process library calls.
- **FR-20:** System SHALL NOT expose LLM generation itself via MCP — the MCP boundary is limited to data access, consistent with Architecture ADR-06.

### 6.6 Model Abstraction & Tiering (revised from v1.0's "Model Abstraction")
- **FR-21:** System SHALL use a model provider abstraction layer supporting at minimum: Anthropic Claude and Azure OpenAI.
- **FR-22:** System SHALL allow provider switching via environment variable without code changes.
- **FR-23:** System SHALL support per-agent model configuration, defaulting to a lower-cost model (Claude Haiku 4.5 / gpt-4o-mini) for Router, Retrieval, and Q&A Drafting agents, and a higher-capability model (Claude Sonnet 5 / gpt-4o) for the Commentary Drafting and Critic agents.
- **FR-24:** The eval harness SHALL validate, not assume, that the lower-cost model tier meets faithfulness/relevance thresholds on the golden dataset before it is treated as the default for a given agent role.

### 6.7 Cost & Rate Guardrails (new)
- **FR-25:** System SHALL enforce a configurable per-session query cap.
- **FR-26:** System SHALL enforce a configurable per-IP rate limit at the API layer.
- **FR-27:** System SHALL track cumulative daily cost and reject new agent-orchestrated requests once a configurable daily ceiling is reached, returning a clear unavailability message rather than failing silently or allowing unbounded spend.

---

## 7. Non-Functional Requirements

| Requirement | Specification |
|-------------|---------------|
| Response latency (P95) | ≤ 8 seconds end-to-end, full agent loop including any retry/revision |
| Uptime | ≥ 99% for demo/portfolio use |
| Data privacy | No uploaded data persisted beyond session; no data sent to third-party logging services beyond Langfuse trace metadata |
| Model version pinning | Exact model version logged with every agent step; no auto-upgrades in production |
| Prompt versioning | All prompt templates versioned in code; changes tracked in git |
| Audit trail | Every response traceable from query → routing → retrieval (incl. retries) → generation → critique (incl. revisions) → eval |
| Deployment topology | Single backend/MCP replica in v1 (documented constraint, see Non-Goals) |
| Cost governance | Per-session, per-IP, and daily spend limits enforced automatically, not monitored manually |

---

## 8. Out of Scope (Explicit)

| Feature | Reason |
|---------|---------|
| User authentication / SSO | v2; not needed for portfolio deployment |
| Live ERP connector | v2; requires enterprise integration scope |
| Chart / visualization output | v2; adds frontend complexity without demonstrating core AI PM signal |
| Fine-tuned models | v2; triggers full SR 11-7 model validation lifecycle |
| Multi-file / multi-period joins | v2; requires data modeling layer |
| Multi-replica / horizontal scaling | v2; requires Redis + pgvector or Azure AI Search |
| Agent orchestration framework (LangGraph etc.) | Deferred until agent graph complexity exceeds what a hand-rolled state machine can cleanly express (Architecture ADR-08) |

---

## 9. Success Criteria (v1.0 Launch)

A v1.0 is considered successful when:

1. A user can upload a synthetic FP&A dataset and receive a grounded, cited answer to at least 20 distinct natural language queries, routed through the full agent pipeline.
2. Commentary Mode produces a reviewable variance narrative for at least 5 cost centers, each passing (or being correctly refused by) the Critic Agent.
3. Every response has a Langfuse trace visible in the observability dashboard, with per-agent cost and latency breakdown.
4. The eval harness runs against the 25-case golden dataset and produces a pass/fail report, including a Haiku-vs-Sonnet cost/quality comparison for the Q&A drafting role.
5. The application is deployed and publicly accessible via a URL (Azure Container Apps primary), with rate limiting and cost ceilings active.
6. The architecture document, including all nine ADRs, is published publicly (GitHub README or docs site).
7. The MCP server (`fpa-data-mcp`) is a genuinely separate, independently runnable component — not an in-process module dressed up as one.

---

## 10. Open Questions

| # | Question | Owner | Due |
|---|----------|-------|-----|
| OQ-01 | Should Commentary Mode output be structured JSON or streaming markdown? *(Resolved v1.0: structured JSON — see Architecture ADR-02.)* | Adedotun | Resolved |
| OQ-02 | What is the right confidence threshold for escalation? 0.6 is a starting point; calibrate against golden dataset. | Eval design | After first eval run |
| OQ-03 | Azure OpenAI vs. Anthropic API as the default provider? | Adedotun | Resolved — Anthropic primary given Haiku/Sonnet tiering story; Azure OpenAI supported and demoed via same abstraction |
| OQ-04 | Should the human review queue persist across sessions (requires a DB) or be session-scoped only? | Adedotun | Architecture doc |
| OQ-05 (new) | Is a 25-case golden dataset sufficient, or should it be expanded before claiming the ≤5% hallucination target has real statistical meaning? | Adedotun | Before final eval report is published |
| OQ-06 (new) | Does the AWS App Runner + Bedrock deployment ship in v1 (stretch goal) or slip to a documented v1.1? | Adedotun | After Azure deployment is stable |

---

## 11. Appendix: SR 11-7 Alignment Notes

SR 11-7 (Supervisory Guidance on Model Risk Management) applies to any model used in a financial institution's decision-making. This product is designed as a **decision-support tool**, not a decision-making tool — all outputs are advisory and require human review before use. The following design choices are SR 11-7-informed:

- **Model version pinning, per agent:** Every agent step logs the exact model used. No silent upgrades.
- **Confidence gating with a hard refusal path:** Low-confidence responses are surfaced or refused, never silently suppressed or shown as more certain than warranted.
- **Human-in-the-loop:** Commentary Mode outputs require human review before use; refused drafts are routed to review rather than discarded.
- **Audit trail, per agent:** Full prompt + context + response logging at each orchestration step enables post-hoc validation of not just the final answer but the path taken to reach it.
- **Prompt versioning:** Prompt templates are version-controlled per agent role; changes are tracked.
- **Scope limitation:** The Router Agent explicitly refuses out-of-scope queries before any downstream cost is incurred, rather than attempting to answer.
- **Cost governance as a control (new):** Spend limits are treated as a governance requirement, not purely an operational concern — an ungoverned-cost system is itself a form of unmanaged risk in a regulated context.

These are not compliance claims — they are design principles appropriate for a portfolio artifact demonstrating governance-aware AI product thinking.
