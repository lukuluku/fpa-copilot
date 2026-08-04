"""
Evaluation metrics for the FP&A Copilot.
Simple heuristic-based scoring (Phase 6).
Production would use DeepEval or similar.
"""

import re
from typing import Any


def check_faithfulness(answer: str, expected_elements: list[str]) -> tuple[bool, float]:
    """
    Check if answer contains expected elements (simple heuristic).
    Returns (passed, confidence_score).
    """
    if not answer:
        return False, 0.0

    answer_lower = answer.lower()
    found_count = 0

    for element in expected_elements:
        if element.lower() in answer_lower:
            found_count += 1

    # All elements must be present
    if not expected_elements:
        # No specific elements required - score based on length and structure
        return True, 0.7 if len(answer) > 100 else 0.4

    if found_count == len(expected_elements):
        return True, 0.9
    elif found_count >= len(expected_elements) * 0.7:
        return True, 0.7
    else:
        return False, found_count / len(expected_elements) if expected_elements else 0.0


def check_hallucination(answer: str) -> tuple[bool, float]:
    """
    Check for hallucination (invented numbers/facts).
    Returns (is_hallucinated, confidence_score).
    """
    if not answer:
        return False, 1.0

    # Simple heuristic: look for unsourced numbers
    # Real numbers should have context like "per", "from", "chunk", "row"
    numbers = re.findall(r'\$[\d,]+|\d+\.?\d*%', answer)

    if not numbers:
        return False, 1.0

    answer_lower = answer.lower()
    citation_keywords = ["per ", "from ", "chunk", "row", "based on", "according to", "cite"]
    has_citations = any(keyword in answer_lower for keyword in citation_keywords)

    if has_citations:
        return False, 0.9
    else:
        # Numbers without citations - potential hallucination
        return True, 0.6


def check_relevance(answer: str, query: str) -> tuple[bool, float]:
    """
    Check if answer is relevant to the query.
    Returns (is_relevant, confidence_score).
    """
    if not answer or not query:
        return False, 0.0

    # Simple heuristic: check for keyword overlap
    query_words = set(query.lower().split())
    answer_words = set(answer.lower().split())

    # Remove common words
    common = {"what", "was", "the", "a", "an", "is", "are", "in", "for", "of", "and", "or"}
    query_words -= common
    answer_words -= common

    if not query_words:
        return True, 0.5

    overlap = len(query_words & answer_words)
    relevance_score = min(overlap / len(query_words), 1.0)

    return relevance_score > 0.2, relevance_score


def check_refusal_accuracy(answer: str, should_pass: bool) -> tuple[bool, float]:
    """
    Check if refusal decision was accurate.
    Returns (correct_decision, confidence_score).
    """
    if not answer:
        answer = ""

    is_refused = "scope" in answer.lower() or "cannot" in answer.lower() or "unable" in answer.lower()

    if should_pass and not is_refused:
        return True, 0.95
    elif not should_pass and is_refused:
        return True, 0.95
    elif should_pass and is_refused:
        return False, 0.3  # Should have answered but refused
    else:
        return False, 0.3  # Should have refused but answered


def evaluate_response(
    answer: str,
    query: str,
    expected_elements: list[str],
    should_pass: bool,
) -> dict:
    """
    Evaluate a response across multiple dimensions.
    Returns dict with scores for each metric.
    """
    # For out-of-scope queries, only check refusal accuracy
    if not should_pass:
        refusal_pass, refusal_score = check_refusal_accuracy(answer, should_pass)
        return {
            "overall_pass": refusal_pass,
            "overall_score": refusal_score,
            "faithfulness": {"pass": True, "score": 1.0, "note": "N/A for refusal"},
            "hallucination": {"is_hallucinated": False, "score": 1.0, "note": "N/A for refusal"},
            "relevance": {"pass": True, "score": 1.0, "note": "N/A for refusal"},
            "refusal_accuracy": {
                "pass": refusal_pass,
                "score": refusal_score,
                "note": "Correctly refused out-of-scope" if refusal_pass else "Incorrectly answered or refused"
            },
        }

    # For in-scope queries, check all metrics
    faithfulness_pass, faithfulness_score = check_faithfulness(answer, expected_elements)
    hallucination_is_hallucinated, hallucination_score = check_hallucination(answer)
    relevance_pass, relevance_score = check_relevance(answer, query)
    refusal_pass, refusal_score = check_refusal_accuracy(answer, should_pass)

    # Combine scores into an overall pass/fail
    # All metrics must pass for overall pass
    overall_pass = (
        faithfulness_pass and
        not hallucination_is_hallucinated and
        relevance_pass and
        refusal_pass
    )

    return {
        "overall_pass": overall_pass,
        "overall_score": (
            faithfulness_score * 0.4 +
            (1.0 - hallucination_score) * 0.3 +
            relevance_score * 0.2 +
            refusal_score * 0.1
        ),
        "faithfulness": {
            "pass": faithfulness_pass,
            "score": faithfulness_score,
            "note": "Contains expected elements"
        },
        "hallucination": {
            "is_hallucinated": hallucination_is_hallucinated,
            "score": hallucination_score,
            "note": "Numbers are sourced/cited"
        },
        "relevance": {
            "pass": relevance_pass,
            "score": relevance_score,
            "note": "Answers the question"
        },
        "refusal_accuracy": {
            "pass": refusal_pass,
            "score": refusal_score,
            "note": "Correct scope decision"
        },
    }


if __name__ == "__main__":
    # Test
    answer = "Engineering headcount variance was -5.6%, per chunk_000. Budget was $450,000 and actuals were $475,000."
    query = "What was the engineering headcount variance?"
    expected = ["Engineering", "-5.6%", "$475,000"]

    result = evaluate_response(answer, query, expected, should_pass=True)
    print(f"Overall pass: {result['overall_pass']}")
    print(f"Overall score: {result['overall_score']:.2f}")
    for metric, scores in result.items():
        if metric not in ["overall_pass", "overall_score"]:
            print(f"  {metric}: {scores}")
