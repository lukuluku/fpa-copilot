"""FastAPI application for FP&A Copilot Q&A system."""

import os
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uuid

from backend.guardrails import GuardrailsManager
from backend.agents.orchestrator import AgentOrchestrator
from src.data_loader import load_csv, create_chunks
from src.embedding_service import EmbeddingService


# Initialize FastAPI
app = FastAPI(title="FP&A Copilot", version="0.7")

# Initialize guardrails
guardrails = GuardrailsManager(
    requests_per_minute=int(os.getenv("RATE_LIMIT_PER_MIN", "20")),
    max_queries_per_session=int(os.getenv("QUERY_CAP_PER_SESSION", "50")),
    max_daily_cost=float(os.getenv("DAILY_COST_CEILING", "10.0")),
)

# Initialize data & services (lazy, per request to avoid global state)
_orchestrator = None


def get_orchestrator():
    """Get or initialize orchestrator (lazy initialization)."""
    global _orchestrator
    if _orchestrator is None:
        # Load data
        rows = load_csv("data/sample_data.csv")
        chunks = create_chunks(rows)

        # Initialize embeddings
        embedder = EmbeddingService()
        chunk_texts = [chunk.text for chunk in chunks]
        embeddings = embedder.embed(chunk_texts)

        # Build DataFrame-like structure for orchestrator
        import pandas as pd
        df = pd.DataFrame({
            "chunk": chunk_texts,
            "metadata": [chunk.metadata for chunk in chunks],
        })

        # Initialize orchestrator with data
        _orchestrator = AgentOrchestrator(df, embeddings)

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
        # Run orchestrator
        orchestrator = get_orchestrator()
        result = orchestrator.run(query)

        # Construct response
        return QueryResponse(
            query=query,
            answer=result.get("answer", ""),
            refusal_reason=result.get("refusal_reason"),
            guardrails_status=guardrails.get_status(client_ip, session_id),
            traces=result.get("traces", {}),
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
