"""FastAPI application for FP&A Copilot Q&A system."""

import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid

from backend.guardrails import GuardrailsManager
from backend.agents.orchestrator import AgentOrchestrator
from backend.services.trace_emitter import TraceEmitter
from src.data_loader import load_csv, create_chunks
from src.embedding_service import EmbeddingService
from src.retrieval import FAISSRetrieval


# Initialize FastAPI
app = FastAPI(title="FP&A Copilot", version="0.7")

# CORS — allow local frontend dev and deployed origins
_cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:3001"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize guardrails
guardrails = GuardrailsManager(
    requests_per_minute=int(os.getenv("RATE_LIMIT_PER_MIN", "20")),
    max_queries_per_session=int(os.getenv("QUERY_CAP_PER_SESSION", "50")),
    max_daily_cost=float(os.getenv("DAILY_COST_CEILING", "10.0")),
)

# Orchestrator — lazily initialised on first request
_orchestrator = None
_trace_emitter = None


def get_orchestrator() -> AgentOrchestrator:
    """Get or initialise orchestrator (lazy, singleton per process)."""
    global _orchestrator, _trace_emitter
    if _orchestrator is None:
        rows = load_csv("data/sample_budget_data.csv")
        chunks = create_chunks(rows)
        embedding_service = EmbeddingService()
        faiss_retrieval = FAISSRetrieval(chunks, embedding_service)
        _trace_emitter = TraceEmitter()
        _orchestrator = AgentOrchestrator(faiss_retrieval, _trace_emitter)
    return _orchestrator


# Request/Response models
class QueryRequest(BaseModel):
    query: str
    session_id: str | None = None  # If not provided, generate one


class QueryResponse(BaseModel):
    query: str
    answer: str
    refusal_reason: str | None = None
    guardrails_status: dict
    traces: dict  # Per-agent traces


@app.middleware("http")
async def client_ip_middleware(request: Request, call_next):
    """Extract client IP for rate limiting."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else request.client.host
    request.state.client_ip = client_ip
    response = await call_next(request)
    return response


@app.post("/query")
async def query_endpoint(req: QueryRequest, request: Request) -> QueryResponse:
    """Main Q&A endpoint with guardrails."""

    client_ip = request.state.client_ip
    session_id = req.session_id or str(uuid.uuid4())
    query = req.query

    # Estimate cost (rough: 0.005 per query)
    estimated_cost = 0.005

    # Check guardrails
    allowed, reason = guardrails.check_all(client_ip, session_id, estimated_cost)

    if not allowed:
        raise HTTPException(status_code=429, detail={
            "error": "Guardrail violated",
            "reason": reason,
            "guardrails_status": guardrails.get_status(client_ip, session_id),
        })

    try:
        orchestrator = get_orchestrator()
        result = orchestrator.run(query)

        # Build per-agent trace dict for the frontend governance sidebar.
        # Keys are "agent_N" so the sidebar can iterate in order.
        traces = {
            f"step_{i}": {
                "agent": step.agent,
                "model": step.model,
                "duration_ms": round(step.latency_ms),
                "input_tokens": step.input_tokens,
                "output_tokens": step.output_tokens,
                "cost": step.cost_usd,
            }
            for i, step in enumerate(result.context_used and [] or [])
            # context_used holds retrieval chunks; per_agent is on the trace.
            # We surface per_agent via the emitter's last trace instead.
        }

        # Pull per_agent from the most recent emitted trace
        if _trace_emitter and _trace_emitter.traces:
            last_trace = _trace_emitter.traces[-1]
            traces = {
                f"step_{i}": {
                    "agent": step.agent,
                    "model": step.model,
                    "duration_ms": round(step.latency_ms),
                    "input_tokens": step.input_tokens,
                    "output_tokens": step.output_tokens,
                    "cost": step.cost_usd,
                }
                for i, step in enumerate(last_trace.per_agent)
            }

        return QueryResponse(
            query=query,
            answer=result.answer or "",
            refusal_reason=result.refusal_reason,
            guardrails_status=guardrails.get_status(client_ip, session_id),
            traces=traces,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status")
async def status_endpoint(request: Request):
    """Health check + guardrails status."""
    client_ip = request.state.client_ip

    return {
        "status": "ok",
        "version": "0.7",
        "guardrails": {
            "rate_limit_per_min": guardrails.rate_limit.requests_per_minute,
            "query_cap_per_session": guardrails.query_cap.max_queries_per_session,
            "daily_cost_ceiling": guardrails.cost_ceiling.max_daily_cost,
        },
        "client_ip": client_ip,
    }


@app.get("/guardrails/{session_id}")
async def guardrails_status_endpoint(session_id: str, request: Request):
    """Get guardrails status for a session."""
    client_ip = request.state.client_ip

    return {
        "session_id": session_id,
        "client_ip": client_ip,
        "status": guardrails.get_status(client_ip, session_id),
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom exception handler for guardrail violations."""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail if isinstance(exc.detail, dict) else {"error": exc.detail},
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
