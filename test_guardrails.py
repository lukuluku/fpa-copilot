#!/usr/bin/env python3
"""Test guardrails: rate limiting, query caps, daily cost ceiling."""

from backend.guardrails import GuardrailsManager

def test_rate_limit():
    """Test per-IP rate limiting."""
    print("\n=== Testing Rate Limit (20 req/min) ===")
    guardrails = GuardrailsManager(requests_per_minute=3)  # Reduced for testing

    ip = "192.168.1.1"

    # First 3 requests should pass
    for i in range(3):
        allowed, msg = guardrails.check_all(ip, "session1", 0.01)
        print(f"  Request {i+1}: {'✓ Allowed' if allowed else '✗ Rejected'}")
        assert allowed, f"First 3 requests should be allowed"

    # 4th request should fail
    allowed, msg = guardrails.check_all(ip, "session1", 0.01)
    print(f"  Request 4: {'✗ Rejected' if not allowed else '✓ Allowed'} (expected rejection)")
    assert not allowed, f"4th request should be rejected"
    print(f"  Reason: {msg}")


def test_query_cap():
    """Test per-session query limit."""
    print("\n=== Testing Query Cap (50 queries/session) ===")
    guardrails = GuardrailsManager(max_queries_per_session=2)  # Reduced for testing

    session = "session-123"

    # First 2 queries should pass
    for i in range(2):
        allowed, msg = guardrails.check_all("ip1", session, 0.01)
        print(f"  Query {i+1}: {'✓ Allowed' if allowed else '✗ Rejected'}")
        assert allowed, f"First 2 queries should be allowed"

    # 3rd query should fail
    allowed, msg = guardrails.check_all("ip1", session, 0.01)
    print(f"  Query 3: {'✗ Rejected' if not allowed else '✓ Allowed'} (expected rejection)")
    assert not allowed, f"3rd query should be rejected"
    print(f"  Reason: {msg}")


def test_cost_ceiling():
    """Test daily cost ceiling."""
    print("\n=== Testing Daily Cost Ceiling ($10/day) ===")
    guardrails = GuardrailsManager(max_daily_cost=0.10)  # $0.10 for testing

    ip = "192.168.1.2"

    # 5 queries at $0.02 each = $0.10 (at limit)
    for i in range(5):
        allowed, msg = guardrails.check_all(ip, "session2", 0.02)
        print(f"  Query {i+1} ($0.02): {'✓ Allowed' if allowed else '✗ Rejected'}")
        assert allowed, f"Query {i+1} should be allowed (spent ${i*0.02:.2f}, limit $0.10)"

    # 6th query should fail (would exceed $0.10)
    allowed, msg = guardrails.check_all(ip, "session2", 0.02)
    print(f"  Query 6 ($0.02): {'✗ Rejected' if not allowed else '✓ Allowed'} (expected rejection)")
    assert not allowed, f"6th query should be rejected (at cost ceiling)"
    print(f"  Reason: {msg}")

    # Status check
    status = guardrails.get_status(ip, "session2")
    print(f"  Spent: ${status['cost_ceiling']['spent_today']:.2f}")
    print(f"  Remaining: ${status['cost_ceiling']['remaining']:.2f}")


def test_multiple_ips_isolation():
    """Test that guardrails are isolated per IP."""
    print("\n=== Testing IP Isolation ===")
    guardrails = GuardrailsManager(requests_per_minute=2, max_daily_cost=0.05)

    ip1 = "192.168.1.1"
    ip2 = "192.168.1.2"

    # IP1: Use up rate limit
    for i in range(2):
        allowed, _ = guardrails.check_all(ip1, "session", 0.01)
        assert allowed, f"IP1 request {i+1} should be allowed"

    # IP1: Rate limit exceeded
    allowed, _ = guardrails.check_all(ip1, "session", 0.01)
    assert not allowed, "IP1 should be rate limited"
    print(f"  IP1: ✗ Rate limited")

    # IP2: Should still be allowed (different IP)
    allowed, _ = guardrails.check_all(ip2, "session", 0.01)
    assert allowed, "IP2 should NOT be rate limited"
    print(f"  IP2: ✓ Allowed (separate from IP1)")


def test_guardrails_status():
    """Test status reporting."""
    print("\n=== Testing Status Reporting ===")
    guardrails = GuardrailsManager()

    ip = "192.168.1.1"
    session = "session-test"

    # Make a query
    guardrails.check_all(ip, session, 0.005)

    # Check status
    status = guardrails.get_status(ip, session)
    print(f"  Rate limit: {status['rate_limit']['remaining_requests']}/{status['rate_limit']['max_per_minute']}")
    print(f"  Query cap: {status['query_cap']['used_queries']}/{status['query_cap']['max_per_session']}")
    print(f"  Daily cost: ${status['cost_ceiling']['spent_today']:.4f}/${status['cost_ceiling']['max_daily']:.2f}")

    assert status['rate_limit']['remaining_requests'] == 19, "Should have 19 requests remaining"
    assert status['query_cap']['used_queries'] == 1, "Should have used 1 query"
    assert status['cost_ceiling']['spent_today'] == 0.005, "Should have spent $0.005"


if __name__ == "__main__":
    test_rate_limit()
    test_query_cap()
    test_cost_ceiling()
    test_multiple_ips_isolation()
    test_guardrails_status()
    print("\n✓ All guardrails tests passed!")
