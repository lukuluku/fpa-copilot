# Build Log — FP&A Copilot

How to use this file: every time you hit a real fork in the road (not every commit —
just the ones where you genuinely weighed two options), add an entry using the template
below, **before** you write the code, not after. If you can't fill in "what I'd say if
challenged" honestly, you don't understand the decision well enough yet — that's a signal
to slow down, not a formality to skip.

At the end of each phase, also answer the three retro questions. That's where the real
learning gets pinned down — without it, you'll build the thing but not retain why.

---

## Decision Entry Template (copy this for each real fork)

```
### [Phase X] Decision: <short title>

**Date:**
**What I was trying to do:**
**Options I considered:**
  1. ...
  2. ...
**What I chose:**
**Why:**
**Trade-off I'm accepting:**
**What I'd say if challenged on this in an interview:**
**Did this match what the architecture doc predicted? (yes / no / partially — and why)**
```

---

## Phase Checklist & Retro Questions

### Phase 0 — Skeleton
- [ ] CSV upload works
- [ ] One hardcoded query → one LLM call → printed answer
- [ ] Both providers (Anthropic + Azure OpenAI) tested via the gateway abstraction
- **Retro:** What broke first? What took longer than expected — env/keys, or the actual LLM call?

### Phase 1 — Retrieval
- [ ] FAISS embedding + similarity search working
- [ ] Tried at least 3 queries where retrieval visibly got it wrong
- **Retro:** What did a bad retrieval result actually look like? Did it fail loudly or silently?

### Phase 2 — Agents (Router, Retriever, Drafter — no Critic yet)
- [ ] Three functions, called in sequence, no loop yet
- [ ] Tested at least one clearly out-of-scope query through the Router
- **Retro:** Does the Router genuinely need its own LLM call, or could a cheaper check do it? (This is a real fork — log it either way.)

### Phase 3 — Critic + Orchestrator Loop
- [x] Retry-once-on-low-coverage implemented
- [x] Revise-once-on-failed-critique implemented
- [x] Hard refusal path implemented and tested
- **Retro:** Threshold felt about right on real queries — 12 of 307 traces hit `refused_faithfulness`, which is a believable rate for a prototype dataset. Found and fixed a bug in this phase: revision path used `per_agent[-1] =` (overwrite) instead of `add_agent_step()` (append), silently dropping the revision drafting entry and understating `total_cost_usd` on all `draft_revised: true` traces. 29 historical traces have understated costs; not backfilled (pre-fix dev scaffolding, not used for real cost claims).

### Phase 4 — Observability (Langfuse)
- [x] Per-agent trace (model, latency, cost) logged for every request
- [x] Can you answer "why did this response cost $X?" by looking at the trace alone, without checking code?
- **Retro:** Two things logged that weren't in the §3.6 schema: `_last_trace_id` stored on the emitter (needed to build the dashboard URL outside an active span context — `get_trace_url()` returns None without it), and `answer_present: bool` in the root span output (cleaner than parsing `outcome` string in the UI). Three things that broke during wiring: wrong Langfuse region (US vs cloud.langfuse.com), child spans fired outside parent context (v4 requires all children inside the root `with` block), and `propagate_attributes()` doesn't exist in v4.14.2. Trace confirmed live in dashboard: `https://us.cloud.langfuse.com/project/cmsi58m5i0iutad0j1vwh3ehe/traces/4a2baa60a935487bbf34945ebe3841cb`.

### Phase 5 — MCP Server
- [x] Data access pulled out of backend into standalone `fpa-data-mcp`
- [x] Backend now calls it as an MCP client
- **Retro:** The extra hop added ~7,300ms per retrieval call — all subprocess cold-start (sentence-transformers + FAISS rebuilding from scratch per request). End-to-end orchestrator went from ~8s to ~24s with MCP active. Very noticeable. Default kept as `use_mcp=False`; MCP path is wired and tested via the `use_mcp=True` flag but not activated for production traffic until a persistent TCP/SSE server replaces the subprocess approach.

### Phase 6 — Eval Harness
- [ ] Golden dataset run end-to-end
- [ ] Haiku-vs-Sonnet comparison run for the Q&A drafter role
- **Retro:** Did the eval confirm or contradict the tiered-model assumption in ADR-07? This is the most important retro in the whole build — don't skip it.

### Phase 7 — Guardrails, Frontend, Deployment
- [ ] Rate limits + cost ceiling enforced and tested (try to break it yourself)
- [ ] Frontend governance sidebar shows real per-agent cost/latency
- [ ] Deployed and reachable via public URL
- **Retro:** What's the one limitation you'd tell a skeptical interviewer about unprompted, before they ask?

---

## Quick-reference: what "explain it in the room" actually requires

For each ADR in the architecture doc, you should be able to answer, in plain language, without notes:
1. What was the alternative you didn't pick?
2. What does the choice you made cost you?
3. What would make you revisit this decision later?

If you can answer those three for an ADR, you're ready to defend it. If you can't yet,
that ADR needs another pass — either in the doc, or by actually building the alternative
far enough to feel the difference.
