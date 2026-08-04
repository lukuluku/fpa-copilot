# Architecture Notes — Implementation Insights & Updates to Architecture Doc

This document supplements the original `fpa-copilot-architecture.md` with implementation details discovered during Phases 0-6.

---

## ADRs: Reality vs. Design

### ADR-01: FAISS In-Memory (Session-Scoped)

**Design:** In-memory FAISS index, session-scoped, single replica only.

**Reality:**
- ✅ Works as designed for 14-row demo dataset
- ✅ Embedding + indexing happens at startup (~2s latency)
- ⚠️ Retrieval is fast (~100ms per query after warmup)
- ❌ Not tested at scale (what happens with 100k+ rows?)

**Trade-off holding up?** Yes. For Phase 1-6 scope, in-memory is appropriate.

**When to revisit:** If/when we move beyond demo data, pgvector + Redis becomes necessary.

---

### ADR-03: Model-Agnostic Gateway

**Design:** Abstract gateway supports multiple providers (Anthropic, Azure OpenAI, etc.)

**Reality:**
- ✅ Implemented AnthropicGateway with per-agent model config
- ✅ Can override models via env vars (EVAL_USE_SONNET for A/B testing)
- ⚠️ Only Anthropic implemented; Azure OpenAI not wired yet
- ⚠️ Per-agent overrides work but a bit ad-hoc (env vars, not config file)

**Trade-off holding up?** Yes. The abstraction is sound. Adding Azure OpenAI would be straightforward.

**Improvement:** Consider a config file (YAML) for per-agent model selection instead of env vars.

---

### ADR-06: MCP Boundary for Data Access

**Design:** Data access (retrieval, lookups, audit logs) exposed via MCP server; backend calls via MCP client.

**Reality:**
- ✅ Architecture is clean: data layer behind boundary
- ✅ MCP server is standalone and independently runnable
- ❌ Demo uses subprocess (6s latency overhead, not production-ready)
- ⚠️ Would need persistent server (TCP/SSE) for production use
- ⚠️ Latency overhead is real but documented

**Trade-off holding up?** Yes. The boundary is architecturally sound.

**What would change for production:**
1. Start MCP server on port 8100 (persistent process)
2. MCPClient connects via HTTP or SSE, not subprocess
3. Latency drops from 6s (demo) to ~10-50ms (network RTT)

---

### ADR-07: Tiered Models (Haiku for Routing/Retrieval/Q&A, Sonnet for Commentary/Critic)

**Design:** Use cheaper Haiku for non-critical paths, Sonnet for high-stakes (Commentary, Critic).

**Reality from Phase 6 eval:**
- ✅ Works for routing (Haiku can classify scope 100%)
- ✅ Works for retrieval (Haiku can assess coverage)
- ❌ **Q&A drafting: Haiku at 70.6% vs 80% target** ← UNDER QUESTION
- ✅ Commentary at 67% (acceptable for draft mode)
- ✅ Critic at 100% pass rate (Sonnet working well)

**Trade-off holding up?** Partially. Routing and retrieval tiers are sound. **Q&A tier needs reassessment.**

**What Phase 7 needs to decide:**
- Option A: Keep Haiku for Q&A, improve prompts (cheaper, risky)
- Option B: Upgrade Q&A to Sonnet (16x cost increase, guaranteed quality)
- Option C: Use Sonnet only for complex queries, Haiku for simple ones (hybrid)

**Recommendation for Phase 7:** Validate with 1-2 prompt iterations. If Q&A doesn't reach 80%, upgrade to Sonnet.

---

### ADR-08: Hand-Rolled Orchestrator (No Framework)

**Design:** ~150 lines of explicit state machine instead of LangGraph.

**Reality:**
- ✅ Code is readable and testable
- ✅ Control flow is explicit (no magic)
- ✅ Easy to instrument with tracing (Phase 4 was simple)
- ⚠️ Duplication in retry/revision logic
- ⚠️ Doesn't scale if we add more agents or loops

**Trade-off holding up?** Yes. For Phase 1-6 scope (4 agents, 2-iteration loop), hand-rolling was correct.

**When to reconsider:** If Phase 7+ adds 5+ agents or complex branching, a framework becomes justified.

---

### ADR-09: Cost Guardrails as Governance Feature

**Design:** Per-session query cap, per-IP rate limit, daily cost ceiling (not implemented yet).

**Reality:**
- ✅ Cost calculator is working (Phases 4-6)
- ✅ Per-query cost is visible in traces
- ❌ Guardrails themselves not yet implemented (Phase 7 task)
- ⚠️ Design decision is sound, but execution is pending

**What's needed for Phase 7:**
- Rate limiter at API layer (sliding window, per IP)
- Session query cap (in-memory counter)
- Daily cost ceiling (check running total before each request)

---

## Empirical Findings

### Retrieval Behavior

**Query → FAISS similarity scores:**
- Direct match (engineering headcount): 0.39-0.48
- Aggregation (cost centers, totals): 0.40-0.46
- Ambiguous (vague keywords): 0.40-0.44
- Out-of-domain (weather): 0.37-0.39

**Insight:** All queries score in 0.37-0.48 range. No query scores > 0.65 (high confidence threshold in architecture doc was unrealistic).

**Action:** Phase 6 lowered thresholds to 0.60 (sufficient), 0.45 (marginal), < 0.45 (low). This is more realistic.

### Agent Latency Profile

Per-agent latencies (single query, Haiku drafting):
```
Router:     1.1s  (simple classification)
Retrieval:  3.7s  (embedding + search + LLM assessment)
Drafting:   1.5s  (LLM generation)
Critic:     1.5s  (LLM review)
─────────────────
Total:      7.8s
```

**Bottleneck:** Retrieval (3.7s). Mostly embeddings (2-3s warmup).

**Opportunity:** Cache embeddings between queries. Embedding the same data twice is wasteful.

### Routing Accuracy

**Out-of-scope queries:** 100% correct refusal
- "What's the weather?"
- "How do I invest?"
- "Can you help with taxes?"

**Insight:** Router is excellent at boundary enforcement. Not a bottleneck.

### Critic Behavior

**Verdicts observed:**
- PASS: 60% of drafts (Haiku drafting)
- REVISE: 35% of drafts
- REFUSE: 5% of drafts (hard refusal)

**Insight:** Critic is appropriately strict. Not over-accepting, not over-rejecting.

### Multi-Agent Bias

Original architecture concern: "Haiku judging its own draft (same model judging same model) creates bias."

**Reality:** We use Sonnet for Critic. Haiku (drafting) is judged by Sonnet (critic), not itself.

**Result:** No detected same-model bias. This design choice is working.

---

## Prompt Evolution

### Router Prompt (v1)

**Current:** Straightforward classification with clear examples of in-scope/out-of-scope.

**Effectiveness:** 100% on out-of-scope refusal.

**Status:** ✅ No changes needed.

### Retrieval Prompt (v1 → v1 tuned)

**Original thresholds:**
- > 0.65: sufficient
- 0.50-0.65: marginal
- < 0.50: low

**Tuned thresholds (Phase 6):**
- > 0.60: sufficient
- 0.45-0.60: marginal
- < 0.45: low

**Reason:** Observed scores cluster 0.39-0.48; original thresholds were unrealistic.

**Status:** ✅ Updated and working.

### Q&A Drafting Prompt (v1 → v1 improved)

**Added guidance:**
- Explicit "list ALL items" for aggregation
- Explicit "show numeric basis" for ranking
- Explicit citation format expectations

**Impact:** Q&A accuracy 64.7% → 70.6% (+6 percentage points)

**Status:** ⚠️ Improved but still below target. Needs more work.

### Critic Prompt (v1)

**Current:** PASS/REVISE/REFUSE verdicts with confidence scores.

**Observations:**
- Haiku drafts: ~35% require revision
- After revision: ~90% pass (second pass)
- Overall: 5% hard refusal (appropriate strictness)

**Status:** ✅ Working well, no changes needed.

---

## Evaluation Insights

### Metric Limitations

**Faithfulness (keyword matching):** 
- ✅ Catches hallucinations
- ❌ Fails on synonyms ("exceed" vs "exceeded")
- ❌ Misses partial matches ("over budget by 10%" contains "budget" but not exact phrase)

**Hallucination (citation presence):**
- ✅ Catches completely unsourced claims
- ❌ Misses subtle hallucinations (wrong number sourced correctly)
- ❌ False positives if answer cites correctly but in unexpected format

**Relevance (keyword overlap):**
- ✅ Simple to compute
- ❌ Doesn't measure semantic relevance
- ❌ Fails on paraphrases or synonyms

**Recommendation for Phase 7 eval:** Use DeepEval or Anthropic's eval SDKs for more sophisticated semantic understanding.

### Golden Dataset Bias

Dataset was created by me with finance knowledge. Potential biases:
- Might underweight obvious queries (might be easier than I think)
- Might overweight edge cases I invented (might be unrealistic)
- Test cases are tightly coupled to our specific dataset structure

**Mitigation for Phase 7:** Expand dataset with cases from actual users (if available) or domain experts.

---

## Cost Analysis

### Current Cost Model (Haiku drafting)

Per query:
```
Router:    $0.0004  (0.2s * $0.80/1M input tokens, 50 output tokens)
Retrieval: $0.0006  (0.3s * $0.80/1M input tokens, 100 output tokens)
Drafting:  $0.0009  (0.5s * $0.80/1M input tokens, 124 output tokens)
Critic:    $0.0038  (0.5s * $3.00/1M input tokens, 150 output tokens)
──────────────────
Total:     $0.0057  (~$57 per 10k queries, ~$684/year)
```

### If Upgraded to Sonnet Q&A

```
Drafting:  $0.0082  (instead of $0.0009, 10x)
Total:     $0.0122  (~$122 per 10k queries, ~$1,464/year)
```

### Sonnet for Everything (Worst Case)

```
Total:     $0.0250+ (~$250 per 10k queries, ~$3,000/year)
```

**Cost scaling:** Haiku is 20-40x cheaper than all-Sonnet. ADR-07 is financially sound IF Haiku quality is acceptable.

---

## What the Architecture Doc Got Right

1. **Orchestrator as state machine** — Exactly what we built. Scalable to ~10-20 agents before needing a framework.
2. **Bounded iterations** — Retry once, revise once. In practice, this works: most drafts pass on first try.
3. **Critic agent distinction** — Using Sonnet for critique while Haiku drafts. Prevents same-model bias.
4. **MCP for data boundary** — Clean separation works in practice. Latency is high in demo mode but architecture is sound.
5. **Per-agent tracing** — Exactly what we implemented. Enables cost/latency breakdown and governance.

## What Needs Updating

1. **ADR-07 assumption on Haiku Q&A** — Needs validation. Phase 6 shows it's borderline.
2. **Retrieval score thresholds** — Original thresholds (0.65, 0.50) were unrealistic. Phase 6 tuned to (0.60, 0.45).
3. **Eval sophistication** — Architecture doc mentions DeepEval. We built heuristics for Phase 6. Phase 7 should integrate real eval.
4. **Prompt versioning** — Architecture doc mentions "prompt templates version-controlled." We have v1, but v1 has sub-versions (tuned). Need more rigorous versioning.

---

## Lessons Learned for Phase 7+

### Lesson 1: Start with Cheap Models, Measure Before Upgrading

ADR-07 assumed Haiku would be sufficient. We only know it's marginal because of Phase 6 eval. **Don't guess. Measure.**

### Lesson 2: Evaluation Should Happen Early

Phase 6 came late (at the end). Should have built eval framework in Phase 2-3 to catch issues sooner.

### Lesson 3: Retrieval is Hard; It's Not Just "Find Similar Chunks"

Retrieval score thresholds, query reformulation, coverage assessment — all of this needed tuning. Architecture doc underestimated complexity.

### Lesson 4: Cost Visibility is Powerful

Phase 4 (tracing) made it obvious that Sonnet costs 10x Haiku. Without this, ADR-07 trade-off would be invisible.

### Lesson 5: Prompts Matter More Than Model Choice (Sometimes)

6% Q&A improvement from prompt changes shows that prompt engineering can close some gaps. Not a silver bullet, but powerful.

---

## Open Questions for Phase 7+

1. **ADR-07 Finalization:** Haiku or Sonnet for Q&A drafting?
2. **Eval Integration:** DeepEval or custom metrics?
3. **Horizontal Scaling:** Move from session-scoped to persistent storage + multi-replica?
4. **Cost Controls:** Implement rate limiting, query caps, daily ceilings?
5. **User Feedback Loop:** How do we measure real-world accuracy once deployed?

---

## Next Steps for Phase 7

- [ ] Decide on ADR-07 (Haiku vs Sonnet) based on prompt iteration results
- [ ] Implement cost guardrails (rate limiting, caps, ceilings)
- [ ] Build Next.js frontend with governance sidebar
- [ ] Integrate Langfuse (currently using local traces)
- [ ] Deploy to Azure Container Apps (single replica, as per ADR-01)
- [ ] Plan for Phase 8: horizontal scaling, DeepEval integration, real-world measurement

