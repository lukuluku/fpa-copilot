"""
Trace emitter — logs traces locally and optionally sends to Langfuse.
For Phase 4, we log locally. Phase 4+ will add Langfuse integration.
"""

import json
import os
from datetime import datetime
from backend.models.trace import TraceRecord


class TraceEmitter:
    """Emits traces to local storage and optionally to Langfuse."""

    def __init__(self, output_dir: str = "traces"):
        self.output_dir = output_dir
        self.traces: list[TraceRecord] = []

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Langfuse config (optional)
        self.langfuse_enabled = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"
        self.langfuse_public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        self.langfuse_secret_key = os.getenv("LANGFUSE_SECRET_KEY")

        if self.langfuse_enabled and (not self.langfuse_public_key or not self.langfuse_secret_key):
            print("Warning: LANGFUSE_ENABLED but keys not set. Traces will be logged locally only.")
            self.langfuse_enabled = False

    def emit(self, trace: TraceRecord):
        """
        Emit a completed trace.
        Logs locally and optionally sends to Langfuse.
        """
        self.traces.append(trace)

        # Log to local JSON file
        self._log_locally(trace)

        # Send to Langfuse if enabled
        if self.langfuse_enabled:
            self._send_to_langfuse(trace)

    def _log_locally(self, trace: TraceRecord):
        """Log trace to a local JSON file."""
        filename = f"{self.output_dir}/trace_{trace.trace_id}.json"
        with open(filename, "w") as f:
            json.dump(trace.to_dict(), f, indent=2)

    def _send_to_langfuse(self, trace: TraceRecord):
        """Send trace to Langfuse (not implemented in Phase 4)."""
        # In Phase 4+, this would call the Langfuse API
        # For now, just a placeholder
        pass

    def get_summary(self) -> dict:
        """Get summary statistics for all emitted traces."""
        if not self.traces:
            return {
                "total_traces": 0,
                "total_cost": 0.0,
                "total_latency_ms": 0.0,
            }

        total_cost = sum(t.total_cost_usd for t in self.traces)
        total_latency = sum(t.total_latency_ms for t in self.traces)
        successful = sum(1 for t in self.traces if t.outcome == "success")

        return {
            "total_traces": len(self.traces),
            "successful": successful,
            "refused": len(self.traces) - successful,
            "total_cost_usd": total_cost,
            "avg_cost_per_trace": total_cost / len(self.traces) if self.traces else 0.0,
            "total_latency_ms": total_latency,
            "avg_latency_ms": total_latency / len(self.traces) if self.traces else 0.0,
        }
