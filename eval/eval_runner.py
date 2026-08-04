"""
Eval runner — executes orchestrator against golden dataset and scores results.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_loader import load_csv, create_chunks
from src.embedding_service import EmbeddingService
from src.retrieval import FAISSRetrieval
from backend.agents.orchestrator import AgentOrchestrator
from backend.services.trace_emitter import TraceEmitter
from eval.metrics import evaluate_response


class EvalRunner:
    """Run evaluation against golden dataset."""

    def __init__(self):
        """Initialize orchestrator and load dataset."""
        # Setup orchestrator
        rows = load_csv("data/sample_budget_data.csv")
        chunks = create_chunks(rows)
        embedding_service = EmbeddingService()
        faiss_retrieval = FAISSRetrieval(chunks, embedding_service)
        trace_emitter = TraceEmitter()
        self.orchestrator = AgentOrchestrator(faiss_retrieval, trace_emitter)

        # Load golden dataset
        with open("eval/data/golden_dataset.json") as f:
            self.test_cases = json.load(f)

    def run_evaluation(self) -> dict:
        """Run all test cases and return results."""
        results = {
            "total_cases": len(self.test_cases),
            "passed": 0,
            "failed": 0,
            "by_category": {},
            "cases": [],
        }

        for test_case in self.test_cases:
            case_id = test_case["case_id"]
            query = test_case["query"]
            expected_elements = test_case.get("expected_elements", [])
            should_pass = test_case.get("should_pass", True)
            category = test_case.get("category", "unknown")

            # Run through orchestrator
            orch_result = self.orchestrator.run(query)
            answer = orch_result.answer or f"REFUSED: {orch_result.refusal_reason}"

            # Evaluate
            eval_result = evaluate_response(answer, query, expected_elements, should_pass)

            # Track by category
            if category not in results["by_category"]:
                results["by_category"][category] = {"passed": 0, "failed": 0, "cases": []}

            case_result = {
                "case_id": case_id,
                "category": category,
                "query": query,
                "passed": eval_result["overall_pass"],
                "score": eval_result["overall_score"],
                "answer": answer[:200] if answer else "",
                "orch_success": orch_result.success,
                "metrics": {k: v for k, v in eval_result.items() if k not in ["overall_pass", "overall_score"]},
            }

            results["cases"].append(case_result)
            results["by_category"][category]["cases"].append(case_result)

            if eval_result["overall_pass"]:
                results["passed"] += 1
                results["by_category"][category]["passed"] += 1
            else:
                results["failed"] += 1
                results["by_category"][category]["failed"] += 1

        return results


if __name__ == "__main__":
    import time

    print("Starting evaluation...", file=sys.stderr)
    start = time.time()

    runner = EvalRunner()
    results = runner.run_evaluation()

    elapsed = time.time() - start

    # Print summary
    print(f"\nEvaluation complete ({elapsed:.2f}s)")
    print(f"  Total: {results['total_cases']}")
    print(f"  Passed: {results['passed']} ({100*results['passed']/results['total_cases']:.1f}%)")
    print(f"  Failed: {results['failed']} ({100*results['failed']/results['total_cases']:.1f}%)")

    print("\nBy category:")
    for category, stats in results["by_category"].items():
        total = stats["passed"] + stats["failed"]
        pct = 100 * stats["passed"] / total if total > 0 else 0
        print(f"  {category:<25} {stats['passed']}/{total} ({pct:>5.1f}%)")

    # Return full results
    print("\nFull results:")
    print(json.dumps(results, indent=2))
