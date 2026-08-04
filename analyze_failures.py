"""Analyze which Q&A cases are failing and why."""
from dotenv import load_dotenv
load_dotenv()

from src.data_loader import load_csv, create_chunks
from src.embedding_service import EmbeddingService
from src.retrieval import FAISSRetrieval
from backend.agents.orchestrator import AgentOrchestrator
from backend.services.trace_emitter import TraceEmitter
from eval.metrics import evaluate_response
import json

# Setup
rows = load_csv("data/sample_budget_data.csv")
chunks = create_chunks(rows)
embedding_service = EmbeddingService()
faiss_retrieval = FAISSRetrieval(chunks, embedding_service)
trace_emitter = TraceEmitter()
orchestrator = AgentOrchestrator(faiss_retrieval, trace_emitter)

# Load test cases
with open("eval/data/golden_dataset.json") as f:
    test_cases = json.load(f)

# Run only Q&A cases (not refusal/commentary)
qa_cases = [c for c in test_cases if c.get("category") not in ["out_of_scope_refusal", "commentary"]]

print("=" * 90)
print("FAILING Q&A CASES - ROOT CAUSE ANALYSIS")
print("=" * 90)

failing = []
for case in qa_cases:
    result = orchestrator.run(case["query"])
    answer = result.answer or f"REFUSED: {result.refusal_reason}"
    
    eval_result = evaluate_response(
        answer, case["query"], case.get("expected_elements", []), case.get("should_pass", True)
    )
    
    if not eval_result["overall_pass"]:
        failing.append((case, answer, eval_result))

print(f"\nTotal Q&A cases: {len(qa_cases)}")
print(f"Failing: {len(failing)}")
print(f"Pass rate: {100*(len(qa_cases)-len(failing))/len(qa_cases):.1f}%")

print("\n" + "=" * 90)
for case, answer, eval_result in failing:
    print(f"\n❌ {case['case_id']} ({case['category']})")
    print(f"   Query: {case['query']}")
    print(f"   Expected: {case.get('expected_elements', [])}")
    print(f"   Score: {eval_result['overall_score']:.3f}")
    print(f"   Answer: {answer[:150]}...")
    
    # Why did it fail?
    if case.get("should_pass"):
        issues = []
        if not eval_result["faithfulness"]["pass"]:
            issues.append(f"Missing expected elements")
        if eval_result["hallucination"]["is_hallucinated"]:
            issues.append(f"Contains unsourced numbers")
        if not eval_result["relevance"]["pass"]:
            issues.append(f"Low keyword overlap")
        print(f"   Root causes: {', '.join(issues) if issues else 'Unknown'}")
