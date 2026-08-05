#!/usr/bin/env python3
"""Investigate why Sonnet performed worse than Haiku on Q&A task.

Hypothesis: Extended thinking (ThinkingBlock) is interfering with output quality.
Test: Compare Sonnet vs Haiku on sample queries with detailed analysis.
"""

import os
from dotenv import load_dotenv
from anthropic import Anthropic
import json

load_dotenv()
API_KEY = os.getenv("ANTHROPIC_API_KEY")
client = Anthropic(api_key=API_KEY)

# Test queries from our eval set
TEST_QUERIES = [
    {
        "name": "direct_lookup",
        "query": "What was the engineering headcount variance in Q3?",
        "context": "Engineering: Budget $500k, Actuals $480k, Variance $20k",
        "expected": "Should answer: $20k variance"
    },
    {
        "name": "aggregation",
        "query": "Which cost centers had the largest total variances?",
        "context": "Engineering: $20k, Marketing: $100k, Sales: $50k",
        "expected": "Should list all three: Marketing ($100k), Sales ($50k), Engineering ($20k)"
    },
    {
        "name": "comparison",
        "query": "What was the best performing cost center?",
        "context": "Engineering: 4% variance, Marketing: 33% variance, Sales: 12.5% variance",
        "expected": "Should identify Engineering as best (lowest variance)"
    }
]

SYSTEM_PROMPT = """You are a finance Q&A assistant. Answer using ONLY the provided context.
For aggregation queries: list ALL items, not just top ones.
For ranking queries: show numeric basis for ranking.
Ground all numbers in the context provided."""

def test_model(model_name, test_query, context):
    """Test a model on a single query. Return response details."""
    print(f"\n{'='*70}")
    print(f"Testing: {model_name}")
    print(f"Query: {test_query}")
    print(f"Context: {context}")
    print(f"{'='*70}")

    user_prompt = f"Context: {context}\n\nQuestion: {test_query}"

    # Build kwargs based on model
    kwargs = {
        "model": model_name,
        "max_tokens": 16000 if "sonnet" in model_name.lower() else 1024,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_prompt}],
    }

    # Don't pass temperature for Sonnet
    if "sonnet" not in model_name.lower():
        kwargs["temperature"] = 0.7

    response = client.messages.create(**kwargs)

    # Analyze response structure
    print(f"\nResponse structure:")
    print(f"  Stop reason: {response.stop_reason}")
    print(f"  Content blocks: {len(response.content)}")

    for i, block in enumerate(response.content):
        block_type = type(block).__name__
        print(f"    [{i}] {block_type}", end="")

        if block_type == "TextBlock":
            print(f" (text length: {len(block.text)})")
            print(f"      Preview: {block.text[:100]}")
        elif block_type == "ThinkingBlock":
            print(f" (thinking length: {len(block.thinking)})")
            print(f"      Preview: {block.thinking[:100]}")
        else:
            print()

    # Extract text response
    text_content = None
    thinking_content = None

    for block in response.content:
        if type(block).__name__ == "TextBlock":
            text_content = block.text
        elif type(block).__name__ == "ThinkingBlock":
            thinking_content = block.thinking

    print(f"\nFinal answer:")
    if text_content:
        print(f"  {text_content}")
    else:
        print(f"  [NO TEXT RESPONSE - only thinking]")

    print(f"\nToken usage:")
    print(f"  Input: {response.usage.input_tokens}")
    print(f"  Output: {response.usage.output_tokens}")
    print(f"  Total: {response.usage.input_tokens + response.usage.output_tokens}")

    if thinking_content:
        print(f"\nThinking tokens: ~{len(thinking_content.split()) * 1.3:.0f} (estimated)")
        print(f"Thinking preview: {thinking_content[:150]}...")

    return {
        "model": model_name,
        "text": text_content,
        "thinking": thinking_content,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "stop_reason": response.stop_reason,
    }


def compare_models(query_name, query, context, expected):
    """Compare Haiku vs Sonnet on same query."""
    print(f"\n\n{'#'*70}")
    print(f"# Test Case: {query_name}")
    print(f"# Expected: {expected}")
    print(f"{'#'*70}")

    haiku_result = test_model("claude-haiku-4-5-20251001", query, context)
    sonnet_result = test_model("claude-sonnet-5", query, context)

    # Analysis
    print(f"\n\n{'*'*70}")
    print(f"ANALYSIS: {query_name}")
    print(f"{'*'*70}")

    print(f"\nHaiku:")
    print(f"  Output: {haiku_result['text'][:100] if haiku_result['text'] else '[NO TEXT]'}")
    print(f"  Tokens: {haiku_result['output_tokens']} output")
    print(f"  Thinking: No")

    print(f"\nSonnet:")
    print(f"  Output: {sonnet_result['text'][:100] if sonnet_result['text'] else '[NO TEXT]'}")
    print(f"  Tokens: {sonnet_result['output_tokens']} output")
    print(f"  Thinking: {'Yes' if sonnet_result['thinking'] else 'No'}")

    if sonnet_result['thinking']:
        print(f"  Thinking length: {len(sonnet_result['thinking'])} chars")

    # Verdict
    haiku_has_answer = bool(haiku_result['text'])
    sonnet_has_answer = bool(sonnet_result['text'])

    print(f"\nVerdicts:")
    if haiku_has_answer and not sonnet_has_answer:
        print(f"  ⚠️  PROBLEM: Sonnet produced no text (only thinking)")
    elif haiku_has_answer and sonnet_has_answer:
        if len(haiku_result['text']) > len(sonnet_result['text']):
            print(f"  ✓ Both answered, Haiku more thorough")
        elif len(sonnet_result['text']) > len(haiku_result['text']):
            print(f"  ✓ Both answered, Sonnet more thorough")
        else:
            print(f"  ✓ Both answered similarly")
    else:
        print(f"  ❌ Both failed to answer")

    return {
        "query": query_name,
        "haiku": haiku_result,
        "sonnet": sonnet_result,
    }


def main():
    print("\n" + "="*70)
    print("SONNET INVESTIGATION: Why did it score 52.9% vs Haiku's 70.6%?")
    print("="*70)

    results = []
    for test in TEST_QUERIES:
        result = compare_models(
            test["name"],
            test["query"],
            test["context"],
            test["expected"]
        )
        results.append(result)

    # Summary
    print(f"\n\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")

    haiku_answered = sum(1 for r in results if r['haiku']['text'])
    sonnet_answered = sum(1 for r in results if r['sonnet']['text'])
    sonnet_thinking = sum(1 for r in results if r['sonnet']['thinking'])

    print(f"\nHaiku responses: {haiku_answered}/{len(results)} had text output")
    print(f"Sonnet responses: {sonnet_answered}/{len(results)} had text output")
    print(f"Sonnet used thinking: {sonnet_thinking}/{len(results)} times")

    print(f"\nKey findings:")
    if sonnet_answered < haiku_answered:
        print(f"  ⚠️  Sonnet produced fewer text responses than Haiku")
        print(f"  → Extended thinking may be causing output token starvation")
    if sonnet_thinking > 0:
        print(f"  ⚠️  Sonnet used extended thinking blocks")
        print(f"  → Could disable thinking for this use case")
    if haiku_answered == len(results) and sonnet_answered < len(results):
        print(f"  ✓ Haiku reliable, Sonnet inconsistent")

    print(f"\nRecommendations:")
    print(f"  1. Test Sonnet without extended thinking (if possible)")
    print(f"  2. Increase max_tokens further to allow thinking + output")
    print(f"  3. Use different prompt for Sonnet (optimize for reasoning)")
    print(f"  4. Or: Accept that Haiku is optimal for this task")

    # Save results
    with open("/tmp/sonnet_investigation.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nDetailed results saved to /tmp/sonnet_investigation.json")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
