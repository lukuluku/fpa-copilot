"""
Orchestrator variant with Sonnet for Q&A drafting (instead of Haiku).
Used to test ADR-07: does Sonnet improve Q&A accuracy?
"""

from backend.agents.orchestrator import AgentOrchestrator


class OrchestratorSonnetQA(AgentOrchestrator):
    """
    Same orchestrator but upgrades Q&A drafting to Sonnet.
    Used to A/B test the model tier assumption.
    """

    def run(self, query: str):
        """Run orchestrator with Sonnet for Q&A drafting."""
        result = super().run(query)

        # Find the drafting step and upgrade its model
        for step in result.get("per_agent", []):
            if step.get("agent") == "drafting":
                step["model"] = "claude-sonnet-5"
                # Recalculate cost for Sonnet
                from backend.services.cost_calculator import calculate_cost
                step["cost_usd"] = calculate_cost(
                    "claude-sonnet-5",
                    step.get("input_tokens", 500),
                    step.get("output_tokens", 150),
                )

        return result
