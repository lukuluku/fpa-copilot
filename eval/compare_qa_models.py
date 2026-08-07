"""
A/B test: Haiku vs Sonnet for Q&A drafting.
Validates ADR-07 assumption: is Haiku sufficient or should we use Sonnet?
"""

import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from eval.eval_runner import EvalRunner


def run_eval_with_model(model_name: str) -> dict:
    """Run evaluation with a specific Q&A drafting model."""
    # Set the model override
    os.environ["LLM_MODEL_DRAFTER_QA"] = model_name

    # Force reimport of gateway to pick up new env var
    import importlib
    import backend.services.llm_gateway
    importlib.reload(backend.services.llm_gateway)

    runner = EvalRunner()
    results = runner.run_evaluation()

    # Clean up
    del os.environ["LLM_MODEL_DRAFTER_QA"]

    return results


def main():
    print("\n" + "=" * 90)
    print("ADR-07 MODEL TIER COMPARISON: Haiku vs Sonnet for Q&A Drafting")
    print("=" * 90)

    print("\n[Haiku] Running evaluation with Q&A drafting on Haiku...")
    haiku_results = run_eval_with_model("claude-haiku-4-5-20251001")

    print(f"  Passed: {haiku_results['passed']}/{haiku_results['total_cases']}")

    print("\n[Sonnet] Running evaluation with Q&A drafting on Sonnet...")
    sonnet_results = run_eval_with_model("claude-sonnet-5")

    print(f"  Passed: {sonnet_results['passed']}/{sonnet_results['total_cases']}")

    # Compare results
    print("\n" + "=" * 90)
    print("COMPARISON")
    print("=" * 90)

    haiku_pass_rate = 100 * haiku_results["passed"] / haiku_results["total_cases"]
    sonnet_pass_rate = 100 * sonnet_results["passed"] / sonnet_results["total_cases"]
    improvement = sonnet_pass_rate - haiku_pass_rate

    print(f"\nHaiku Q&A:   {haiku_results['passed']:>2}/{haiku_results['total_cases']} ({haiku_pass_rate:>5.1f}%)")
    print(f"Sonnet Q&A:  {sonnet_results['passed']:>2}/{sonnet_results['total_cases']} ({sonnet_pass_rate:>5.1f}%)")
    print(f"Improvement: {improvement:>+5.1f}%")

    # Cost comparison (rough estimate)
    # Haiku: ~0.0001 per query
    # Sonnet: ~0.001 per query
    queries_per_month = 10000
    haiku_cost = queries_per_month * 0.0001 * 30
    sonnet_cost = queries_per_month * 0.001 * 30
    cost_increase = sonnet_cost - haiku_cost

    print(f"\nEstimated monthly cost (10k queries):")
    print(f"  Haiku:  ${haiku_cost:>8.2f}")
    print(f"  Sonnet: ${sonnet_cost:>8.2f}")
    print(f"  Delta:  ${cost_increase:>+8.2f} (+{100*cost_increase/haiku_cost:>5.0f}%)")

    # Recommendation
    print("\n" + "=" * 90)
    print("RECOMMENDATION")
    print("=" * 90)

    if improvement < 5:
        print("\n✅ KEEP HAIKU for Q&A drafting")
        print(f"   Sonnet improves accuracy by only {improvement:.1f}%")
        print(f"   Cost increase of {100*cost_increase/haiku_cost:>5.0f}% is not justified")
        print("   ADR-07 is sound: Haiku tier is adequate for Q&A.")
    elif improvement < 15:
        print("\n⚠️  CONSIDER SONNET for Q&A drafting")
        print(f"   Sonnet improves accuracy by {improvement:.1f}%")
        print(f"   Cost increase of {100*cost_increase/haiku_cost:>5.0f}% is moderate")
        print("   Decision depends on quality vs cost priority.")
    else:
        print("\n❌ UPGRADE to SONNET for Q&A drafting")
        print(f"   Sonnet improves accuracy by {improvement:.1f}%")
        print(f"   Cost increase of {100*cost_increase/haiku_cost:>5.0f}% is worth it for {sonnet_pass_rate:.0f}% quality")
        print("   ADR-07 needs revision: Haiku tier is insufficient.")

    # Category breakdown
    print("\n" + "=" * 90)
    print("CATEGORY BREAKDOWN")
    print("=" * 90)

    for category in sorted(haiku_results["by_category"].keys()):
        h_stats = haiku_results["by_category"][category]
        s_stats = sonnet_results["by_category"][category]

        h_total = h_stats["passed"] + h_stats["failed"]
        s_total = s_stats["passed"] + s_stats["failed"]

        h_pct = 100 * h_stats["passed"] / h_total if h_total > 0 else 0
        s_pct = 100 * s_stats["passed"] / s_total if s_total > 0 else 0

        delta = s_pct - h_pct
        status = "↑" if delta > 0 else "↓" if delta < 0 else "="

        print(f"  {status} {category:<28} Haiku {h_pct:>5.1f}% → Sonnet {s_pct:>5.1f}% ({delta:>+5.1f}%)")

    return haiku_results, sonnet_results


if __name__ == "__main__":
    main()
