"""
Trace schema — audit trail for every query execution.
Matches architecture doc §3.6.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
import uuid


@dataclass
class AgentStepMetrics:
    """Metrics for a single agent execution."""
    agent: str  # "router", "retrieval", "drafting", "critic"
    model: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    cost_usd: float


@dataclass
class TraceRecord:
    """Complete trace for a single query execution."""
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    query: str = ""
    agent_path: list[str] = field(default_factory=list)
    retrieval_retried: bool = False
    draft_revised: bool = False
    outcome: str = "success"  # "success" | "refused_scope" | "refused_faithfulness"
    per_agent: list[AgentStepMetrics] = field(default_factory=list)
    confidence_score: float = 0.0
    total_cost_usd: float = 0.0
    total_latency_ms: float = 0.0
    escalated: bool = False
    refusal_reason: str | None = None

    def to_dict(self):
        """Convert to dict, with nested per_agent converted to dicts."""
        data = asdict(self)
        data["per_agent"] = [asdict(m) for m in self.per_agent]
        return data

    def add_agent_step(self, step: AgentStepMetrics):
        """Add a completed agent step."""
        self.per_agent.append(step)
        self.total_cost_usd += step.cost_usd
        self.total_latency_ms += step.latency_ms
