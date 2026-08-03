"""
Router Agent — Classify queries as in-scope or out-of-scope.
"""

import json
import yaml
from pathlib import Path
from dataclasses import dataclass
from backend.services.llm_gateway import get_llm_gateway


@dataclass
class RouterDecision:
    """Decision from the Router Agent."""
    in_scope: bool
    reason: str


class RouterAgent:
    """Router Agent: classifies queries before retrieval."""

    def __init__(self):
        self.llm = get_llm_gateway()
        self.prompt_template = self._load_prompt()

    def _load_prompt(self) -> dict:
        """Load router prompt template."""
        prompt_file = Path("backend/prompts/router_v1.yaml")
        with open(prompt_file) as f:
            return yaml.safe_load(f)

    def route(self, query: str) -> RouterDecision:
        """
        Classify the query as in-scope or out-of-scope.
        Returns a RouterDecision with the classification and reasoning.
        """
        system = self.prompt_template["system"]
        user_template = self.prompt_template["user_template"]
        user = user_template.format(query=query)

        response = self.llm.sync_complete(
            system=system,
            user=user,
            temperature=0.0,  # Deterministic routing
            max_tokens=256,
        )

        try:
            # Strip markdown code fences if present
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```", 2)[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            result = json.loads(text)
            return RouterDecision(
                in_scope=result.get("in_scope", False),
                reason=result.get("reason", "Unknown"),
            )
        except json.JSONDecodeError:
            # Fallback: assume out-of-scope if parsing fails
            return RouterDecision(
                in_scope=False,
                reason=f"Failed to parse router response: {response.text}",
            )


if __name__ == "__main__":
    router = RouterAgent()

    test_queries = [
        "What was the engineering payroll variance in Q3?",
        "Which cost centers are over budget?",
        "What's the weather forecast for next week?",
        "Can you help me with my personal taxes?",
    ]

    for query in test_queries:
        decision = router.route(query)
        print(f"\nQuery: {query}")
        print(f"In-scope: {decision.in_scope}")
        print(f"Reason: {decision.reason}")
