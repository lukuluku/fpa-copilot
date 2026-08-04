"""
Simple comparison: Haiku vs Sonnet for Q&A drafting.
Just runs eval twice with different env var.
"""

import os
import subprocess
import sys
import json


def run_eval_with_env(use_sonnet: bool) -> dict:
    """Run eval with or without Sonnet override."""
    env = os.environ.copy()

    if use_sonnet:
        env["EVAL_USE_SONNET"] = "1"
    else:
        env.pop("EVAL_USE_SONNET", None)

    # Run phase6_test and capture output
    result = subprocess.run(
        [sys.executable, "phase6_test.py"],
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )

    # Extract results from output
    output = result.stdout
    lines = output.split("\n")

    results = {
        "model": "Sonnet" if use_sonnet else "Haiku",
        "passed": 0,
        "total": 0,
        "qa_passed": 0,
        "qa_total": 0,
    }

    for line in lines:
        if "Total cases:" in line:
            results["total"] = int(line.split()[-1])
        if "Passed:" in line and "Total" not in line:
            results["passed"] = int(line.split()[1])
        if "Q&A accuracy" in line:
            # Extract "11/17" format
            parts = line.split("(")
            if len(parts) > 1:
                qa_str = parts[0].strip().split()[-1]
                if "/" in qa_str:
                    results["qa_passed"], results["qa_total"] = map(int, qa_str.split("/"))

    return results


def main():
    print("\n" + "=" * 90)
    print("ADR-07 COMPARISON: Haiku vs Sonnet for Q&A Drafting")
    print("=" * 90)

    print("\n[Running with Haiku Q&A drafting...]")
    haiku = run_eval_with_env(use_sonnet=False)
    print(
        f"  Overall: {haiku['passed']}/{haiku['total']} "
        f"({100*haiku['passed']/haiku['total']:.1f}%)"
    )
    print(
        f"  Q&A only: {haiku['qa_passed']}/{haiku['qa_total']} "
        f"({100*haiku['qa_passed']/haiku['qa_total']:.1f}%)"
    )

    print("\n[Running with Sonnet Q&A drafting...]")
    sonnet = run_eval_with_env(use_sonnet=True)
    print(
        f"  Overall: {sonnet['passed']}/{sonnet['total']} "
        f"({100*sonnet['passed']/sonnet['total']:.1f}%)"
    )
    print(
        f"  Q&A only: {sonnet['qa_passed']}/{sonnet['qa_total']} "
        f"({100*sonnet['qa_passed']/sonnet['qa_total']:.1f}%)"
    )

    # Compare
    print("\n" + "=" * 90)
    print("RESULTS")
    print("=" * 90)

    overall_h = 100 * haiku["passed"] / haiku["total"] if haiku["total"] > 0 else 0
    overall_s = 100 * sonnet["passed"] / sonnet["total"] if sonnet["total"] > 0 else 0
    qa_h = 100 * haiku["qa_passed"] / haiku["qa_total"] if haiku["qa_total"] > 0 else 0
    qa_s = 100 * sonnet["qa_passed"] / sonnet["qa_total"] if sonnet["qa_total"] > 0 else 0

    print(f"\nOverall accuracy:")
    print(f"  Haiku:  {overall_h:>5.1f}%")
    print(f"  Sonnet: {overall_s:>5.1f}%")
    print(f"  Delta:  {overall_s - overall_h:>+5.1f}%")

    print(f"\nQ&A-only accuracy (excl. refusal/commentary):")
    print(f"  Haiku:  {qa_h:>5.1f}%")
    print(f"  Sonnet: {qa_s:>5.1f}%")
    print(f"  Delta:  {qa_s - qa_h:>+5.1f}%")

    # Cost/benefit analysis
    # Rough: Haiku $0.0009/query, Sonnet $0.01/query
    qa_improvement = qa_s - qa_h
    cost_ratio = 10  # Sonnet is ~10x Haiku

    print("\n" + "=" * 90)
    print("DECISION")
    print("=" * 90)

    if qa_improvement < 5:
        print(f"\n✅ KEEP HAIKU for Q&A")
        print(f"   Improvement: {qa_improvement:.1f}% (too small)")
        print(f"   Cost ratio: {cost_ratio}x (not justified)")
        print("   → ADR-07 is sound")

    elif qa_improvement < 10:
        print(f"\n⚠️  MARGINAL: Consider Sonnet")
        print(f"   Improvement: {qa_improvement:.1f}% (moderate)")
        print(f"   Cost ratio: {cost_ratio}x")
        print("   → Decision depends on quality priority")

    else:
        print(f"\n❌ UPGRADE TO SONNET")
        print(f"   Improvement: {qa_improvement:.1f}% (significant)")
        print(f"   Cost ratio: {cost_ratio}x (worth it)")
        print("   → ADR-07 needs revision")


if __name__ == "__main__":
    main()
