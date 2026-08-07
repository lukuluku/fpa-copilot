#!/usr/bin/env python3
"""
Phase 7: Guardrails, API wiring, and governance sidebar test.

Verifies:
  1. All three guardrail types enforce correctly (rate limit, query cap, cost ceiling)
  2. /query endpoint returns correct answer + per-agent traces + guardrails_status
  3. Per-agent traces match the shape the GovernanceSidebar expects
  4. /status endpoint is reachable

Run:
    python phase7_test.py
"""

import os
import sys
from dotenv import load_dotenv
load_dotenv()

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from backend.api import app, guardrails

client = TestClient(app)


def header(title: str):
    print(f"\n{'='*70}\n{title}\n{'='*70}")


def test_status():
    header("Test 1: /status endpoint")
    r = client.get("/status")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    data = r.json()
    assert data["status"] == "ok"
    assert "guardrails" in data
    print(f"  [OK] status=ok, version={data['version']}")
    print(f"  [OK] guardrails config: {data['guardrails']}")


def test_real_query_and_traces():
    header("Test 2: Real query returns answer + per-agent traces")
    r = client.post("/query", json={
        "query": "What was the engineering headcount variance in Q3?",
        "session_id": "phase7-test-session",
    })
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"
    data = r.json()

    # Answer present
    assert data["answer"], "Expected non-empty answer"
    print(f"  [OK] answer: {data['answer'][:80]}...")

    # Traces present with correct shape for GovernanceSidebar
    traces = data["traces"]
    assert traces, "Expected non-empty traces dict"
    for key, step in traces.items():
        for field in ("agent", "model", "duration_ms", "input_tokens", "output_tokens", "cost"):
            assert field in step, f"Trace step missing field '{field}': {step}"
    print(f"  [OK] {len(traces)} agent trace steps:")
    for key, step in traces.items():
        print(f"       {step['agent']:<12} model={step['model']:<30} cost=${step['cost']:.5f}")

    # Guardrails status present
    gs = data["guardrails_status"]
    assert "rate_limit" in gs and "query_cap" in gs and "cost_ceiling" in gs
    print(f"  [OK] guardrails_status present: queries used={gs['query_cap']['used_queries']}")


def test_rate_limit_enforcement():
    header("Test 3: Rate limit — blocks at threshold")
    # Temporarily lower rate limit for the test
    original = guardrails.rate_limit.requests_per_minute
    guardrails.rate_limit.requests_per_minute = 2
    guardrails.rate_limit.requests.clear()

    try:
        for i in range(2):
            r = client.post("/query", json={"query": "test", "session_id": "rl-test"})
            assert r.status_code in (200, 500), f"Request {i+1}: unexpected {r.status_code}"
            print(f"  request {i+1}: {r.status_code} (allowed)")

        # 3rd should be blocked
        r = client.post("/query", json={"query": "test", "session_id": "rl-test"})
        assert r.status_code == 429, f"Expected 429, got {r.status_code}"
        reason = r.json().get("reason", "")
        assert "Rate limit" in reason, f"Unexpected reason: {reason}"
        print(f"  request 3: 429 blocked — '{reason}'")
        print(f"  [OK] Rate limit enforced correctly")
    finally:
        guardrails.rate_limit.requests_per_minute = original
        guardrails.rate_limit.requests.clear()


def test_query_cap_enforcement():
    header("Test 4: Query cap — blocks after session limit")
    original = guardrails.query_cap.max_queries_per_session
    guardrails.query_cap.max_queries_per_session = 2
    session = "cap-test-session-phase7"
    guardrails.query_cap.queries.pop(session, None)

    try:
        for i in range(2):
            r = client.post("/query", json={"query": "test", "session_id": session})
            assert r.status_code in (200, 500)
            print(f"  query {i+1}: {r.status_code} (allowed)")

        r = client.post("/query", json={"query": "test", "session_id": session})
        assert r.status_code == 429, f"Expected 429, got {r.status_code}"
        reason = r.json().get("reason", "")
        assert "query limit" in reason.lower(), f"Unexpected reason: {reason}"
        print(f"  query 3: 429 blocked — '{reason}'")
        print(f"  [OK] Query cap enforced correctly")
    finally:
        guardrails.query_cap.max_queries_per_session = original
        guardrails.query_cap.queries.pop(session, None)


def test_cost_ceiling_enforcement():
    header("Test 5: Daily cost ceiling — blocks when budget exhausted")
    original = guardrails.cost_ceiling.max_daily_cost
    guardrails.cost_ceiling.max_daily_cost = 0.001  # $0.001 — below any real query cost
    ip = "testclient"
    guardrails.cost_ceiling.daily_costs.pop(ip, None)

    try:
        # First query at $0.005 estimated cost should be blocked immediately
        r = client.post("/query", json={"query": "test", "session_id": "cost-test"})
        assert r.status_code == 429, f"Expected 429, got {r.status_code}"
        reason = r.json().get("reason", "")
        assert "cost limit" in reason.lower() or "Daily cost" in reason, f"Unexpected reason: {reason}"
        print(f"  429 blocked — '{reason}'")
        print(f"  [OK] Cost ceiling enforced correctly")
    finally:
        guardrails.cost_ceiling.max_daily_cost = original
        guardrails.cost_ceiling.daily_costs.pop(ip, None)


def main():
    print("=" * 70)
    print("PHASE 7: Guardrails, API wiring, Governance sidebar")
    print("=" * 70)

    test_status()
    test_real_query_and_traces()
    test_rate_limit_enforcement()
    test_query_cap_enforcement()
    test_cost_ceiling_enforcement()

    print("\n" + "=" * 70)
    print("Phase 7 complete — all assertions passed")
    print("=" * 70)
    print("\nChecklist:")
    print("  [x] Rate limits + cost ceiling enforced and tested")
    print("  [x] /query returns per-agent traces in GovernanceSidebar shape")
    print("  [x] API wired to real orchestrator (FAISSRetrieval, TraceEmitter)")
    print("  [ ] Deployed and reachable via public URL — Phase 7 infra item")


if __name__ == "__main__":
    main()
