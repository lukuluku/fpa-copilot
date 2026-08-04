# Implementation Guide — Phases 0-6 Technical Details

This document explains how each component is built and how to modify/extend them.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│  Query Entry Point (Orchestrator)                        │
└────────┬─────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────┐
│ Router Agent     │  Classifies query scope
├──────────────────┤
│ claude-haiku     │  Decision: in-scope / out-of-scope
└────┬──────┬──────┘
     │      └────────── REFUSE (out-of-scope)
     │ (in-scope)
     ▼
┌──────────────────────┐
│ Retrieval Agent      │  Searches FAISS for relevant context
├──────────────────────┤
│ claude-haiku         │  Decision: coverage sufficient? Retry if not
├──────────────────────┤
│ MCP Client           │
│  └─ MCP Server       │  search_financial_data tool
│     └─ FAISS Index   │
└────┬──────────┬──────┘
     │          └────────── Retry once if coverage low
     │
     ▼
┌──────────────────┐
│ Drafting Agent   │  Generates answer from context
├──────────────────┤
│ claude-haiku     │  (or claude-sonnet for testing)
└────┬─────┬──────┘
     │     └────────────── (optional) Revise if critique fails
     │
     ▼
┌──────────────────┐
│ Critic Agent     │  Reviews draft for faithfulness
├──────────────────┤
│ claude-sonnet    │  Decision: PASS / REVISE / REFUSE
└────┬──────┬──────┘
     │      └────────── REFUSE (hard refusal, no partial answer)
     │
     ▼
  Return to User
  + Emit Trace
```

---

## Component Breakdown

### 1. Embedding Service (`src/embedding_service.py`)

**Purpose:** Convert text to vectors for semantic search

**Implementation:**
```python
from sentence_transformers import SentenceTransformer

class EmbeddingService:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
    
    def embed_text(self, text: str) -> list[float]:
        return self.model.encode(text, convert_to_numpy=False).tolist()
    
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [e.tolist() for e in self.model.encode(texts, convert_to_numpy=False)]
```

**To swap for Anthropic embeddings:**
```python
# Change __init__ to:
def __init__(self):
    self.client = Anthropic()

# Change embed_text to:
def embed_text(self, text: str):
    response = self.client.messages.embed(model="text-embedding-3-small", input=text)
    return response.content[0].embedding
```

**Model dimension:** 384 (all-MiniLM-L6-v2)

---

### 2. FAISS Retrieval (`src/retrieval.py`)

**Purpose:** In-memory vector index for semantic search

**Key classes:**
```python
class FAISSRetrieval:
    def __init__(self, chunks: list[Chunk], embedding_service: EmbeddingService):
        # Embeds all chunks
        # Builds FAISS L2 (Euclidean distance) index
    
    def search(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        # 1. Embed query
        # 2. Search FAISS: search(query_vector, k) -> (distances, indices)
        # 3. Convert L2 distance to similarity score: 1 / (1 + distance)
        # 4. Return sorted results
```

**Similarity score formula:**
```
similarity = 1.0 / (1.0 + l2_distance)
```

This converts L2 distance (lower = better) to similarity (higher = better) in range [0, 1).

**Limitations:**
- Single replica only (in-process)
- Session-scoped (lost on restart)
- 14 rows = 14 vectors (demo scale)
- Production: swap for pgvector + Redis (Phase 2+ feature)

---

### 3. LLM Gateway (`backend/services/llm_gateway.py`)

**Purpose:** Abstract LLM provider; allow model swapping

**Key design:**
```python
class AnthropicGateway(LLMGateway):
    DEFAULT_MODELS = {
        "router": "claude-haiku-4-5-20251001",
        "retrieval": "claude-haiku-4-5-20251001",
        "drafter_qa": "claude-haiku-4-5-20251001",
    }
    
    async def complete(self, system, user, model_override=None):
        model = model_override or self.DEFAULT_MODELS["drafter_qa"]
        # Call Anthropic API
```

**To test with Sonnet for Q&A:**
```python
# Set env var:
export EVAL_USE_SONNET=1

# In drafting_agent.py:
if os.getenv("EVAL_USE_SONNET"):
    model_override = "claude-sonnet-5"

response = self.llm.sync_complete(..., model_override=model_override)
```

**Pricing (used in cost calculator):**
```python
PRICING = {
    "claude-haiku-4-5-20251001": {
        "input": 0.80,    # per 1M tokens
        "output": 4.00,
    },
    "claude-sonnet-5": {
        "input": 3.00,
        "output": 15.00,
    },
}
```

---

### 4. Agents (4 separate files in `backend/agents/`)

#### Router Agent (`router_agent.py`)
```
Input: query (str)
Output: RouterDecision {in_scope: bool, reason: str}

Process:
1. Load prompt from backend/prompts/router_v1.yaml
2. Call LLM with JSON response_format
3. Parse JSON, handle errors
```

**Key:** Classifies BEFORE any retrieval/drafting cost. Fast-exits out-of-scope queries.

#### Retrieval Agent (`retrieval_agent.py`)
```
Input: query (str), top_k (int)
Output: RetrievalDecision {
  chunks: list[RetrievalResult],
  coverage_sufficient: bool,
  reformulated_query: str | None,
  reasoning: str
}

Process:
1. Call FAISS: search(query, top_k)
2. Load prompt, format results
3. Call LLM to assess coverage
4. If coverage insufficient AND reformulated_query != None:
   Retry ONCE with reformulated query (Phase 3 integration)
```

**Coverage thresholds (Phase 6 tuned):**
- score > 0.60: SUFFICIENT
- 0.45-0.60: MARGINAL (suggest reformulation)
- < 0.45: LOW (recommend reformulation)

#### Drafting Agent (`drafting_agent.py`)
```
Input: query (str), context: list[RetrievalResult]
Output: DraftingResult {
  answer: str,
  context_used: list[RetrievalResult],
  model_used: str,
  tokens_used: tuple[int, int]
}

Process:
1. Format context: "[chunk_000] score: 0.6\ntext...\n\n[chunk_001]..."
2. Load prompt from backend/prompts/qa_drafter_v1.yaml
3. Call LLM (respects EVAL_USE_SONNET for testing)
4. Return answer + metadata
```

**Prompt evolution:**
- v0: Simple "answer grounded in context"
- v1 (Phase 6): Added guidance on aggregation, ranking, citations

#### Critic Agent (`critic_agent.py`)
```
Input: query (str), draft (str), context: list[RetrievalResult]
Output: CriticDecision {
  verdict: "PASS" | "REVISE" | "REFUSE",
  confidence: float,
  issues: list[str],
  revision_notes: str | None
}

Process:
1. Format context + draft
2. Call LLM with JSON response_format
3. Parse JSON (strip markdown code fences)
4. Return decision
```

**Key:** Uses different model (Sonnet) than Q&A drafting (Haiku) to reduce same-model-judging-itself bias.

---

### 5. Orchestrator (`backend/agents/orchestrator.py`)

**The state machine:**

```python
def run(self, query: str) -> OrchestratorResult:
    trace = TraceRecord()  # Initialize tracing
    
    # Step 1: Router
    route = router.route(query)
    trace.add_agent_step(router_metrics)
    if not route.in_scope:
        return OrchestratorResult.refused(route.reason)
    
    # Step 2: Retrieval (can retry once)
    retrieval = retrieval_agent.retrieve(query)
    if not retrieval.coverage_sufficient and retrieval.reformulated_query:
        retrieval = retrieval_agent.retrieve(retrieval.reformulated_query)
    trace.add_agent_step(retrieval_metrics)
    
    # Step 3: Drafting
    draft = drafting_agent.draft(query, retrieval.chunks)
    trace.add_agent_step(drafting_metrics)
    
    # Step 4: Critic (can revise draft once)
    critique = critic_agent.review(query, draft.answer, retrieval.chunks)
    trace.add_agent_step(critic_metrics)
    
    if critique.verdict == "PASS":
        trace.outcome = "success"
        self.trace_emitter.emit(trace)
        return OrchestratorResult.success(draft.answer, critique.confidence, retrieval.chunks)
    
    # Attempt revision
    if critique.verdict == "REVISE" and not draft_revised:
        draft_revised = True
        draft = drafting_agent.draft(query, retrieval.chunks)  # Retry
        critique = critic_agent.review(query, draft.answer, retrieval.chunks)  # Re-judge
        if critique.verdict == "PASS":
            trace.outcome = "success"
            trace.draft_revised = True
            self.trace_emitter.emit(trace)
            return OrchestratorResult.success(...)
    
    # Hard refusal
    trace.outcome = "refused_faithfulness"
    self.trace_emitter.emit(trace)
    return OrchestratorResult.refused(critique.issues)
```

**Bounded iterations:**
- Retrieval: retry once (0 or 1 retry)
- Drafting: revise once (0 or 1 revision)
- Total: at most 2 iterations, then refuse

**Tracing happens at every step:**
- Router: 1.1s latency, $0.0004 cost
- Retrieval: 3.7s latency, $0.0006 cost
- Drafting: 1.5s latency, $0.0009 cost (Haiku) or $0.01 (Sonnet)
- Critic: 1.5s latency, $0.0038 cost (always Sonnet)

---

### 6. MCP Server (`mcp-server/server.py`)

**Purpose:** Expose data access as a service

**Tools:**
```python
async def search_financial_data(query: str, top_k: int) -> dict:
    # Call self.faiss_retrieval.search(query, top_k)
    # Return: {query, top_k, results: [...], best_match_score}

async def get_cost_center_rows(cost_center_id: str, period: str) -> dict:
    # Filter chunks by cost_center_id and period
    # Return: {cost_center_id, period, row_count, rows}

async def get_audit_log(session_id: str, limit: int) -> dict:
    # Stub: audit log storage not implemented
    # Return: {session_id, limit, entries: []}
```

**Server architecture (demo mode):**
```
Backend Request
    ↓
MCPClient.search_financial_data()
    ↓
subprocess.Popen("python mcp-server/server.py")
    ↓
stdin: {"method": "search_financial_data", "params": {...}}
    ↓
Server: initialize FAISS, process request, output JSON
    ↓
stdout: {"query": ..., "results": [...], "best_match_score": ...}
    ↓
MCPClient parses JSON, returns results
```

**Production mode (not implemented):**
- Server runs persistently on port 8100
- Client connects via TCP/SSE
- Latency: 10-50ms per call (vs 6s for subprocess demo)

---

### 7. Tracing (`backend/models/trace.py` + `backend/services/trace_emitter.py`)

**Trace schema:**
```python
@dataclass
class TraceRecord:
    trace_id: str  # UUID
    session_id: str  # UUID
    timestamp: str  # ISO-8601
    query: str
    agent_path: list[str]  # ["router", "retrieval", "drafting", "critic"]
    retrieval_retried: bool
    draft_revised: bool
    outcome: str  # "success" | "refused_scope" | "refused_faithfulness"
    per_agent: list[AgentStepMetrics]  # [{agent, model, latency_ms, tokens, cost}]
    confidence_score: float  # 0.0-1.0
    total_cost_usd: float
    total_latency_ms: float
```

**Example trace file (`traces/trace_UUID.json`):**
```json
{
  "trace_id": "48c66e3e-...",
  "session_id": "89428280-...",
  "query": "What was the engineering headcount variance in Q3?",
  "agent_path": ["router", "retrieval", "drafting", "critic"],
  "per_agent": [
    {"agent": "router", "model": "claude-haiku-4-5-20251001", "latency_ms": 1116, "cost_usd": 0.00036},
    {"agent": "retrieval", "model": "claude-haiku-4-5-20251001", "latency_ms": 3752, "cost_usd": 0.00064},
    {"agent": "drafting", "model": "claude-haiku-4-5-20251001", "latency_ms": 1500, "cost_usd": 0.00089},
    {"agent": "critic", "model": "claude-sonnet-5", "latency_ms": 1489, "cost_usd": 0.00375}
  ],
  "confidence_score": 0.95,
  "total_cost_usd": 0.0056,
  "total_latency_ms": 7859,
  "outcome": "success"
}
```

---

### 8. Evaluation (`eval/`)

**Golden dataset:** 25 test cases in `eval/data/golden_dataset.json`

**Metrics:** Heuristic-based scoring in `eval/metrics.py`

```python
def evaluate_response(answer, query, expected_elements, should_pass):
    # For out-of-scope: only check refusal accuracy
    # For in-scope: check faithfulness, hallucination, relevance, refusal
    
    # Faithfulness: contains expected_elements?
    # Hallucination: are numbers sourced (has citations)?
    # Relevance: keyword overlap between query and answer?
    # Refusal accuracy: made correct scope decision?
    
    overall_pass = (
        faithfulness_pass and
        not hallucinated and
        relevance_pass and
        refusal_pass
    )
    return {overall_pass, overall_score, per_metric_details}
```

**Results:**
- Overall: 76% (19/25)
- Q&A only: 70.6% (12/17)
- Refusal: 100% (5/5)
- Hallucination detect: 100% (2/2)

---

## How to Extend

### Add a New Agent

1. Create `backend/agents/new_agent.py`:
```python
class NewAgent:
    def __init__(self):
        self.llm = get_llm_gateway()
        self.prompt = load_prompt("backend/prompts/new_agent_v1.yaml")
    
    def decide(self, inputs) -> NewAgentDecision:
        response = self.llm.sync_complete(...)
        return NewAgentDecision(...)
```

2. Create `backend/prompts/new_agent_v1.yaml` with system + user_template

3. Update orchestrator to call it:
```python
def run(self, query):
    ...
    new_decision = new_agent.decide(inputs)
    trace.add_agent_step(new_agent_metrics)
    ...
```

### Swap LLM Provider

Current: Anthropic only

To add Azure OpenAI:
```python
class AzureOpenAIGateway(LLMGateway):
    def __init__(self):
        self.client = AzureOpenAI(...)
    
    async def complete(self, system, user, ...):
        response = self.client.chat.completions.create(...)
        return LLMResponse(...)

# In llm_gateway.py:
def get_llm_gateway():
    provider = os.getenv("LLM_PROVIDER", "anthropic")
    if provider == "anthropic":
        return AnthropicGateway()
    elif provider == "azure_openai":
        return AzureOpenAIGateway()
```

### Improve Retrieval

Current: FAISS with sentence-transformers

Options:
1. Better embeddings: upgrade to OpenAI text-embedding-3-large
2. Persistent index: use pgvector + PostgreSQL
3. Better search: add reranking (bge-reranker-v2-m3)

---

## Common Issues & Fixes

**Issue:** JSON parse errors from Claude responses wrapped in markdown
**Fix:** Strip ` ```json ``` ` wrapper in agent code (already done)

**Issue:** Out-of-scope refusals scoring as failures
**Fix:** Split eval logic by should_pass flag (already done in Phase 6)

**Issue:** FAISS scores always < 0.6 for valid queries
**Fix:** Lower coverage thresholds in retrieval prompt (0.60 → 0.45 for "marginal")

**Issue:** "Tell me about money" correctly refuses but fails ambiguous_query test
**Fix:** Test case definition issue; ambiguous queries should tolerate refusal

---

## Performance Profile

**Latency (single query, Haiku drafting):**
- Router: 1.1s
- Retrieval: 3.7s (includes embedding)
- Drafting: 1.5s
- Critic: 1.5s
- **Total: 7.8s**

**Cost (single query, Haiku drafting):**
- Router: $0.0004
- Retrieval: $0.0006
- Drafting: $0.0009
- Critic: $0.0038
- **Total: $0.0057**

**Scaling:**
- 10,000 queries/month: $57/month (Haiku) vs $500+/month (all Sonnet)
- Latency constant (bottleneck is API calls, not compute)

