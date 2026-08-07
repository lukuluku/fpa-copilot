"""
Trace emitter — logs traces locally and emits to Langfuse.

Local JSON is always written (traces/ directory).
Langfuse emission is enabled when LANGFUSE_ENABLED=true and keys are set.

Langfuse mapping (§3.6):
  TraceRecord         → Langfuse trace  (top-level, query in/answer out)
  AgentStepMetrics    → Langfuse generation (as_type="generation", one per per_agent entry)

The trace_id from TraceRecord is reused as the Langfuse trace ID so local JSON
and Langfuse traces can be correlated by ID.
"""

import json
import os
from datetime import datetime, timezone
from backend.models.trace import TraceRecord, AgentStepMetrics


class TraceEmitter:
    """Emits traces to local storage and optionally to Langfuse."""

    def __init__(self, output_dir: str = "traces"):
        self.output_dir = output_dir
        self.traces: list[TraceRecord] = []
        os.makedirs(output_dir, exist_ok=True)

        # Langfuse config — all three must be present for emission to activate
        self.langfuse_enabled = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY", "")
        host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

        self._langfuse = None
        if self.langfuse_enabled:
            if not public_key or not secret_key:
                print(
                    "Warning: LANGFUSE_ENABLED=true but LANGFUSE_PUBLIC_KEY / "
                    "LANGFUSE_SECRET_KEY are not set. Falling back to local-only."
                )
                self.langfuse_enabled = False
            else:
                try:
                    from langfuse import Langfuse
                    self._langfuse = Langfuse(
                        public_key=public_key,
                        secret_key=secret_key,
                        host=host,
                    )
                except Exception as e:
                    print(f"Warning: Langfuse client failed to initialise ({e}). Local-only.")
                    self.langfuse_enabled = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def emit(self, trace: TraceRecord) -> None:
        """Emit a completed trace — always local, Langfuse if configured."""
        self.traces.append(trace)
        self._log_locally(trace)
        if self.langfuse_enabled and self._langfuse is not None:
            self._send_to_langfuse(trace)

    def get_summary(self) -> dict:
        """Aggregate stats over all traces emitted this session."""
        if not self.traces:
            return {"total_traces": 0, "total_cost": 0.0, "total_latency_ms": 0.0}

        total_cost = sum(t.total_cost_usd for t in self.traces)
        total_latency = sum(t.total_latency_ms for t in self.traces)
        successful = sum(1 for t in self.traces if t.outcome == "success")

        return {
            "total_traces": len(self.traces),
            "successful": successful,
            "refused": len(self.traces) - successful,
            "total_cost_usd": total_cost,
            "avg_cost_per_trace": total_cost / len(self.traces),
            "total_latency_ms": total_latency,
            "avg_latency_ms": total_latency / len(self.traces),
        }

    # ------------------------------------------------------------------
    # Local storage
    # ------------------------------------------------------------------

    def _log_locally(self, trace: TraceRecord) -> None:
        filename = f"{self.output_dir}/trace_{trace.trace_id}.json"
        with open(filename, "w") as f:
            json.dump(trace.to_dict(), f, indent=2)

    # ------------------------------------------------------------------
    # Langfuse emission
    # ------------------------------------------------------------------

    def _send_to_langfuse(self, trace: TraceRecord) -> None:
        """
        Emit one Langfuse trace with one generation span per per_agent entry.

        Structure:
          root span  (name=trace.query, carries §3.6 metadata)
            └─ generation  router
            └─ generation  retrieval
            └─ generation  drafting
            └─ generation  critic
            └─ generation  drafting  (revision path only)
            └─ generation  critic    (revision path only)

        All agent spans are nested inside the root span's with-block — this is
        required by the v4 SDK; start_observation called outside an active context
        raises a context error and the span is dropped.
        """
        from langfuse.types import TraceContext

        lf = self._langfuse

        # Reuse our own trace_id as the Langfuse trace ID so local JSON and
        # Langfuse traces are correlatable by ID without a lookup table.
        trace_id = lf.create_trace_id(seed=trace.trace_id)

        with lf.start_as_current_observation(
            trace_context=TraceContext(trace_id=trace_id),
            name=trace.query,
            as_type="span",
            input={"query": trace.query},
            output={
                "outcome": trace.outcome,
                "answer_present": trace.outcome == "success",
                "refusal_reason": trace.refusal_reason,
            },
            metadata={
                "session_id": trace.session_id,
                "agent_path": trace.agent_path,
                "retrieval_retried": trace.retrieval_retried,
                "draft_revised": trace.draft_revised,
                "confidence_score": trace.confidence_score,
                "total_cost_usd": trace.total_cost_usd,
                "total_latency_ms": trace.total_latency_ms,
                "escalated": trace.escalated,
                # §3.6 eval_scores — populated by Phase 6 eval harness
                "eval_scores": {
                    "faithfulness": 0.0,
                    "answer_relevance": 0.0,
                    "contextual_precision": 0.0,
                },
            },
        ):
            # All agent spans must be created inside this with-block so the
            # SDK can attach them as children of the root span.
            for step in trace.per_agent:
                with lf.start_as_current_observation(
                    name=step.agent,
                    as_type="generation",
                    model=step.model,
                    usage_details={
                        "input": step.input_tokens,
                        "output": step.output_tokens,
                        "total": step.input_tokens + step.output_tokens,
                    },
                    cost_details={
                        "input": _token_cost(step.model, step.input_tokens, output=False),
                        "output": _token_cost(step.model, step.output_tokens, output=True),
                        "total": step.cost_usd,
                    },
                    metadata={
                        "latency_ms": step.latency_ms,
                        "cost_usd": step.cost_usd,
                    },
                ):
                    pass  # span recorded on enter/exit; no body needed

        # Flush synchronously — ensures traces land before process exits.
        # Long-running FastAPI server can remove this; SDK batches automatically.
        lf.flush()

        # Store trace_id so callers can build the dashboard URL.
        # session_id is already in the root span's metadata above.
        self._last_trace_id = trace_id


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

# Input / output price per token (USD) for each model used in the pipeline.
# These mirror calculate_cost() in cost_calculator.py; kept here so the
# Langfuse span can split cost_details into input vs output (Langfuse shows
# them separately in the UI).
_PRICING: dict[str, tuple[float, float]] = {
    # (input_per_token, output_per_token)
    "claude-haiku-4-5-20251001": (0.0000008, 0.0000032),
    "claude-sonnet-5":           (0.000003,  0.000015),
    "claude-haiku-4-5":          (0.0000008, 0.0000032),
    "claude-sonnet-4-5":         (0.000003,  0.000015),
}
_DEFAULT_PRICING = (0.000003, 0.000015)  # fall back to Sonnet rates


def _token_cost(model: str, tokens: int, output: bool) -> float:
    prices = _PRICING.get(model, _DEFAULT_PRICING)
    return round(prices[1 if output else 0] * tokens, 8)
