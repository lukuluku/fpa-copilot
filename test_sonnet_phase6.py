#!/usr/bin/env python3
"""Run all 17 Phase 6 Q&A cases through Sonnet vs Haiku.

Identifies which specific cases Sonnet fails on.
"""

import json
import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Load Phase 6 golden dataset
with open("eval/data/golden_dataset.json") as f:
    GOLDEN_DATA = json.load(f)

# Q&A cases only (exclude refusal/out-of-scope)
QA_CATEGORIES = [
    "direct_lookup",
    "variance_calculation",
    "multi_row_aggregation",
    "commentary",
    "ambiguous_query",
    "edge_case",
    "hallucination_detection",
    "context_grounding"
]

CONTEXT = """
Engineering: Budget $500k, Actuals $480k, Variance $20k (-4%), Headcount: 50
Sales & Marketing: Budget $800k, Actuals $700k, Variance $100k (-12.5%), Headcount: 40
Finance & Operations: Budget $300k, Actuals $280k, Variance $20k (-6.7%), Headcount: 25
"""

def run_test(model, query, context):
    """Run single query through model."""
    system_prompt = """You are a finance Q&A assistant. Answer based ONLY on provided context.
For aggregations: list ALL items matching criteria.
For rankings: show numeric basis.
Ground all claims in the context."""

    user_prompt = f"Context:\n{context}\n\nQuestion: {query}"

    kwargs = {
        "model": model,
        "max_tokens": 16000 if "sonnet" in model.lower() else 1024,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }

    if "sonnet" not in model.lower():
        kwargs["temperature"] = 0.7

    try:
        response = client.messages.create(**kwargs)

        # Extract text
        text_content = None
        for block in response.content:
            if type(block).__name__ == "TextBlock":
                text_content = block.text
                break

        return {
            "text": text_content,
            "tokens": response.usage.output_tokens,
            "stop_reason": response.stop_reason,
            "success": bool(text_content),
        }
    except Exception as e:
        return {
            "text": None,
            "error": str(e),
            "success": False,
        }


def main():
    print("\n" + "="*80)
    print("SONNET vs HAIKU: Full Phase 6 Q&A Test (17 cases)")
    print("="*80)

    results = []
    case_num = 0

    for category in QA_CATEGORIES:
        cases = [c for c in GOLDEN_DATA if c.get("category") == category]

        for case in cases:
            case_num += 1
            query = case["query"]
            case_id = case["case_id"]

            print(f"\n[{case_num}/17] {case_id}: {query[:60]}...")

            # Run both models
            haiku = run_test("claude-haiku-4-5-20251001", query, CONTEXT)
            sonnet = run_test("claude-sonnet-5", query, CONTEXT)

            # Verdict
            haiku_ok = haiku["success"]
            sonnet_ok = sonnet["success"]

            if haiku_ok and sonnet_ok:
                if len(sonnet["text"]) > len(haiku["text"]):
                    verdict = "✓ Both OK, Sonnet better"
                elif len(haiku["text"]) > len(sonnet["text"]):
                    verdict = "✓ Both OK, Haiku better"
                else:
                    verdict = "✓ Both OK, similar"
            elif haiku_ok and not sonnet_ok:
                verdict = "✗ SONNET FAILED"
            elif sonnet_ok and not haiku_ok:
                verdict = "✓ Only Sonnet worked"
            else:
                verdict = "✗✗ Both failed"

            print(f"  {verdict}")
            print(f"  Haiku: {haiku['tokens']} tokens" + (f" | {haiku.get('error', 'OK')}" if haiku.get('error') else ""))
            print(f"  Sonnet: {sonnet['tokens']} tokens" + (f" | {sonnet.get('error', 'OK')}" if sonnet.get('error') else ""))

            results.append({
                "case_id": case_id,
                "category": category,
                "query": query,
                "haiku_ok": haiku_ok,
                "sonnet_ok": sonnet_ok,
                "haiku_tokens": haiku.get("tokens", 0),
                "sonnet_tokens": sonnet.get("tokens", 0),
                "verdict": verdict,
            })

    # Summary
    print(f"\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    haiku_pass = sum(1 for r in results if r["haiku_ok"])
    sonnet_pass = sum(1 for r in results if r["sonnet_ok"])

    print(f"\nPass rates:")
    print(f"  Haiku:  {haiku_pass}/17 ({haiku_pass*100/17:.1f}%)")
    print(f"  Sonnet: {sonnet_pass}/17 ({sonnet_pass*100/17:.1f}%)")

    # Failures
    haiku_failures = [r for r in results if not r["haiku_ok"]]
    sonnet_failures = [r for r in results if not r["sonnet_ok"]]

    if sonnet_failures:
        print(f"\nSonnet failures ({len(sonnet_failures)}):")
        for r in sonnet_failures:
            print(f"  ✗ {r['case_id']}: {r['query'][:60]}")

    if haiku_failures:
        print(f"\nHaiku failures ({len(haiku_failures)}):")
        for r in haiku_failures:
            print(f"  ✗ {r['case_id']}: {r['query'][:60]}")

    # Category breakdown
    print(f"\nBy category:")
    for cat in QA_CATEGORIES:
        cat_results = [r for r in results if r["category"] == cat]
        if cat_results:
            h = sum(1 for r in cat_results if r["haiku_ok"])
            s = sum(1 for r in cat_results if r["sonnet_ok"])
            print(f"  {cat:30} Haiku: {h}/{len(cat_results)}, Sonnet: {s}/{len(cat_results)}")

    # Token analysis
    print(f"\nToken efficiency:")
    haiku_tokens = sum(r["haiku_tokens"] for r in results)
    sonnet_tokens = sum(r["sonnet_tokens"] for r in results)
    print(f"  Haiku total:  {haiku_tokens} tokens ({haiku_tokens/17:.0f} per query)")
    print(f"  Sonnet total: {sonnet_tokens} tokens ({sonnet_tokens/17:.0f} per query)")
    print(f"  Sonnet overhead: {sonnet_tokens/haiku_tokens:.1f}x")

    # Verdict
    print(f"\n" + "="*80)
    print("VERDICT")
    print("="*80)

    if sonnet_pass >= haiku_pass:
        print(f"\n✅ SONNET IS BETTER OR EQUAL")
        print(f"   Sonnet: {sonnet_pass}/17 ({sonnet_pass*100/17:.1f}%)")
        print(f"   Haiku:  {haiku_pass}/17 ({haiku_pass*100/17:.1f}%)")
        print(f"\n   Recommendation: UPGRADE TO SONNET")
        print(f"   Cost increase: {sonnet_tokens/haiku_tokens:.1f}x per query")
        print(f"   Quality gain: +{sonnet_pass - haiku_pass} cases")
    else:
        print(f"\n❌ HAIKU IS STILL BETTER")
        print(f"   Haiku:  {haiku_pass}/17 ({haiku_pass*100/17:.1f}%)")
        print(f"   Sonnet: {sonnet_pass}/17 ({sonnet_pass*100/17:.1f}%)")
        print(f"\n   Recommendation: KEEP HAIKU")
        print(f"   Reason: Sonnet is {haiku_pass - sonnet_pass} cases worse")

    # Save detailed results
    with open("/tmp/sonnet_phase6_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed results saved to /tmp/sonnet_phase6_results.json")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
