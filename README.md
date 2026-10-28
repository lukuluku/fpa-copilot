# FP&A Copilot

A multi-agent Q&A assistant for financial planning & analysis (FP&A) data. Ask a plain-English question about budget-vs-actuals data and get a cited answer — or an honest refusal when the data can't support one.

Every response comes with a **governance sidebar**: which model ran each step, what it cost, how long it took, how confident the system is, and whether the answer had to be retried or revised. The goal is an AI tool a finance team could actually audit, not a black box.

---

## How it works

Each question passes through four agents, coordinated by a hand-rolled orchestrator:

```
Question
   │
   ▼
Router ──────────── out of scope? ──► Refuse
   │
   ▼
Retrieval (FAISS) ─ low coverage? ──► Retry once ──► still low? ──► Refuse
   │
   ▼
Drafting (Haiku)
   │
   ▼
Critic (Sonnet) ─── fails review? ──► Revise once ──► still fails? ──► Refuse
   │
   ▼
Answer + per-agent trace (model, cost, latency, confidence)
```

| Agent | Job | Model |
|---|---|---|
| **Router** | Decides if the question is in scope for FP&A data | Haiku |
| **Retrieval** | Finds relevant rows via vector search, scores coverage | Embeddings + FAISS |
| **Drafting** | Writes the answer with citations to source rows | Haiku |
| **Critic** | Checks the draft is faithful to the data; can force one revision | Sonnet |

**Guardrails** (enforced in FastAPI middleware):
- Per-IP rate limit — 20 requests/minute (sliding window)
- Per-session query cap — 50 queries
- Daily cost ceiling — $10/day

---

## Tech stack

| Layer | Tech |
|---|---|
| Backend | Python 3.12, FastAPI, Uvicorn |
| LLMs | Anthropic Claude (Haiku + Sonnet) via a model-agnostic gateway |
| Retrieval | sentence-transformers + FAISS (in-memory) |
| Data access | Standalone MCP server (`mcp-server/`) — optional |
| Observability | Langfuse (optional) |
| Frontend | Next.js 15, React 18, TypeScript, Tailwind CSS |
| Deployment | Docker; `render.yaml` blueprint included |

---

## Repo structure

```
fpa-copilot/
├── backend/
│   ├── api.py              # FastAPI app: /query, /status, /guardrails/{session_id}
│   ├── guardrails.py       # Rate limit, session cap, cost ceiling
│   ├── agents/             # router, retrieval, drafting, critic, orchestrator
│   ├── prompts/            # Versioned YAML prompt templates
│   ├── services/           # LLM gateway, cost calculator, tracing, MCP client
│   └── models/trace.py     # Per-agent trace schema
├── src/                    # CSV loader, embedding service, FAISS retrieval
├── mcp-server/             # Standalone data-access server (MCP)
├── eval/                   # Eval harness + 25-case golden dataset
├── frontend/               # Next.js UI with governance sidebar
├── data/sample_budget_data.csv
├── fpa-copilot-prd.md            # Product requirements
├── fpa-copilot-architecture.md   # Architecture + ADRs
└── BUILD_LOG_PHASES_0-6.md       # Decision log and phase retros
```

---

## Run it locally

**Prerequisites:** Python 3.12, Node.js 20+, an [Anthropic API key](https://console.anthropic.com/).

### 1. Backend

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then add your ANTHROPIC_API_KEY
python -m uvicorn backend.api:app --reload --port 8000
```

The first start downloads the embedding model and builds the FAISS index, so it takes a little while. Check it's up at http://localhost:8000/status.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. The frontend calls `http://localhost:8000` by default; override it with `NEXT_PUBLIC_API_URL`.

### 3. Run the evals

```bash
python eval/eval_runner.py
```

Runs the 25 golden test cases in `eval/data/golden_dataset.json` and reports routing, Q&A, and refusal accuracy.

---

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | — (required) | Claude API access |
| `RATE_LIMIT_PER_MIN` | `20` | Per-IP request limit |
| `QUERY_CAP_PER_SESSION` | `50` | Max queries per session |
| `DAILY_COST_CEILING` | `10.0` | Daily spend limit in USD |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:3001` | Allowed frontend origins |
| `LANGFUSE_ENABLED` | — | Set `true` to send traces to Langfuse |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_HOST` | — | Langfuse credentials |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend URL (frontend, set at build time) |

Never commit `.env` — it's in `.gitignore`.

---

## Results so far

From the Phase 6 eval harness (25 golden cases):

| Metric | Result |
|---|---|
| Overall accuracy | 76% (19/25) |
| Q&A accuracy | 70.6% (12/17) — target is 80% |
| Routing accuracy | 100% |
| Refusal accuracy | 100% |
| Critic | 60% accepted first pass, 90% after one revision |
| Cost per query | ~$0.006 (Haiku drafting) vs ~$0.012 (Sonnet drafting) |
| Latency | ~8s per query (embedding is the bottleneck) |

**Open question (ADR-07):** Is Haiku good enough for drafting? A follow-up test showed Sonnet performed about the same, which suggests the gap is in prompts and scoring (aggregations and citation formatting are the weak spots), not the model.

---

## Key design decisions

Full reasoning is in [`fpa-copilot-architecture.md`](fpa-copilot-architecture.md) and [`BUILD_LOG_PHASES_0-6.md`](BUILD_LOG_PHASES_0-6.md). The short version:

- **In-memory FAISS, single replica** — simple and fast at demo scale; doesn't scale horizontally.
- **Tiered models** — Haiku for cheap steps, Sonnet only for the Critic. Roughly 20–40x cheaper than all-Sonnet.
- **Hand-rolled orchestrator, not LangGraph** — explicit, readable control flow for 4 agents and a 2-step retry/revise loop.
- **MCP boundary for data access** — clean separation between orchestration and data. Off by default: the subprocess version adds ~7s per lookup until a persistent server replaces it.
- **Batch responses, no streaming** — the Critic can reject a draft, so partial answers are never shown.
- **Cost guardrails as a first-class feature** — required before any public deployment.

---

## Known limitations

- The backend currently answers questions over the bundled `data/sample_budget_data.csv`; the upload page doesn't yet re-index user files on the server.
- Data lives in memory per process, so only one backend instance can run at a time.
- No user authentication.
- On free hosting tiers the backend cold-starts in ~30s (embedding model + index load) and needs enough memory for sentence-transformers.

---

## Roadmap

- [ ] Confirm public deployment
- [ ] Close the Q&A accuracy gap to 80% (aggregation + citation prompts)
- [ ] Wire user CSV/Excel uploads through to the backend index
- [ ] Persistent MCP server (TCP/SSE) instead of subprocess
- [ ] Persistent vector store (e.g. pgvector) to allow multiple instances
- [ ] Authentication and audit log page
