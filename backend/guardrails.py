"""Cost guardrails: rate limiting, query caps, daily cost ceiling."""

import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class IPRateLimit:
    """Per-IP sliding window rate limiter (20 req/min default)."""
    requests_per_minute: int = 20
    window_seconds: int = 60

    # Track requests per IP: {ip: [(timestamp, cost), ...]}
    requests: dict = field(default_factory=lambda: defaultdict(list))

    def is_allowed(self, ip: str, current_cost: float = 0.0) -> bool:
        """Check if IP is within rate limit. Return True if allowed."""
        now = time.time()
        cutoff = now - self.window_seconds

        # Clean old requests
        self.requests[ip] = [(ts, cost) for ts, cost in self.requests[ip] if ts > cutoff]

        # Check limit
        if len(self.requests[ip]) >= self.requests_per_minute:
            return False

        # Record this request
        self.requests[ip].append((now, current_cost))
        return True

    def get_remaining(self, ip: str) -> int:
        """Get remaining requests for IP in current window."""
        now = time.time()
        cutoff = now - self.window_seconds
        self.requests[ip] = [(ts, cost) for ts, cost in self.requests[ip] if ts > cutoff]
        return max(0, self.requests_per_minute - len(self.requests[ip]))


@dataclass
class SessionQueryCap:
    """Per-session query counter (50 queries/session default)."""
    max_queries_per_session: int = 50

    # Track queries per session: {session_id: query_count}
    queries: dict = field(default_factory=dict)

    def is_allowed(self, session_id: str) -> bool:
        """Check if session is within query cap."""
        if session_id not in self.queries:
            self.queries[session_id] = 0

        if self.queries[session_id] >= self.max_queries_per_session:
            return False

        self.queries[session_id] += 1
        return True

    def get_remaining(self, session_id: str) -> int:
        """Get remaining queries for session."""
        count = self.queries.get(session_id, 0)
        return max(0, self.max_queries_per_session - count)

    def get_count(self, session_id: str) -> int:
        """Get query count for session."""
        return self.queries.get(session_id, 0)


@dataclass
class DailyCostCeiling:
    """Daily cost ceiling per IP (prevents budget overruns)."""
    max_daily_cost: float = 10.0  # $10/day default

    # Track daily costs: {ip: {date: total_cost}}
    daily_costs: dict = field(default_factory=lambda: defaultdict(dict))

    def is_allowed(self, ip: str, query_cost: float) -> bool:
        """Check if IP can afford this query within daily ceiling."""
        from datetime import date
        today = str(date.today())

        if ip not in self.daily_costs:
            self.daily_costs[ip] = {}

        current_cost = self.daily_costs[ip].get(today, 0.0)

        if current_cost + query_cost > self.max_daily_cost:
            return False

        # Record the cost
        self.daily_costs[ip][today] = current_cost + query_cost
        return True

    def get_remaining(self, ip: str) -> float:
        """Get remaining budget for IP today."""
        from datetime import date
        today = str(date.today())

        if ip not in self.daily_costs or today not in self.daily_costs[ip]:
            return self.max_daily_cost

        current_cost = self.daily_costs[ip][today]
        return max(0.0, self.max_daily_cost - current_cost)

    def get_spent(self, ip: str) -> float:
        """Get amount spent by IP today."""
        from datetime import date
        today = str(date.today())

        if ip not in self.daily_costs:
            return 0.0

        return self.daily_costs[ip].get(today, 0.0)


class GuardrailsManager:
    """Centralized guardrails: rate limiting + query caps + cost ceiling."""

    def __init__(
        self,
        requests_per_minute: int = 20,
        max_queries_per_session: int = 50,
        max_daily_cost: float = 10.0,
    ):
        self.rate_limit = IPRateLimit(requests_per_minute=requests_per_minute)
        self.query_cap = SessionQueryCap(max_queries_per_session=max_queries_per_session)
        self.cost_ceiling = DailyCostCeiling(max_daily_cost=max_daily_cost)

    def check_all(self, ip: str, session_id: str, estimated_cost: float = 0.0) -> tuple[bool, str]:
        """
        Check all guardrails. Return (allowed: bool, reason: str).
        If not allowed, reason explains which limit was hit.
        """
        # Check rate limit
        if not self.rate_limit.is_allowed(ip, estimated_cost):
            remaining = self.rate_limit.get_remaining(ip)
            return False, f"Rate limit exceeded. Max {self.rate_limit.requests_per_minute} req/min. Retry in 60s."

        # Check query cap
        if not self.query_cap.is_allowed(session_id):
            return False, f"Session query limit exceeded. Max {self.query_cap.max_queries_per_session} queries/session."

        # Check cost ceiling
        if not self.cost_ceiling.is_allowed(ip, estimated_cost):
            remaining = self.cost_ceiling.get_remaining(ip)
            return False, f"Daily cost limit exceeded. Max ${self.cost_ceiling.max_daily_cost:.2f}/day. ${remaining:.2f} remaining."

        return True, ""

    def get_status(self, ip: str, session_id: str) -> dict:
        """Get current guardrails status for this IP/session."""
        return {
            "rate_limit": {
                "remaining_requests": self.rate_limit.get_remaining(ip),
                "max_per_minute": self.rate_limit.requests_per_minute,
            },
            "query_cap": {
                "used_queries": self.query_cap.get_count(session_id),
                "max_per_session": self.query_cap.max_queries_per_session,
                "remaining": self.query_cap.get_remaining(session_id),
            },
            "cost_ceiling": {
                "spent_today": self.cost_ceiling.get_spent(ip),
                "max_daily": self.cost_ceiling.max_daily_cost,
                "remaining": self.cost_ceiling.get_remaining(ip),
            },
        }
