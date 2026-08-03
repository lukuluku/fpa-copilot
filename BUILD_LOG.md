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
- [ ] Retry-once-on-low-coverage implemented
- [ ] Revise-once-on-failed-critique implemented
- [ ] Hard refusal path implemented and tested
- **Retro:** On real queries, did the refusal threshold feel right, too strict, or too loose? Log this even if you don't change it yet.

### Phase 4 — Observability (Langfuse)
- [ ] Per-agent trace (model, latency, cost) logged for every request
- [ ] Can you answer "why did this response cost $X?" by looking at the trace alone, without checking code?
- **Retro:** What did you decide to log that *wasn't* in the architecture doc's trace schema? Why?

### Phase 5 — MCP Server
- [ ] Data access pulled out of backend into standalone `fpa-data-mcp`
- [ ] Backend now calls it as an MCP client
- **Retro:** How much latency did the extra hop actually add? Was it noticeable?

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
