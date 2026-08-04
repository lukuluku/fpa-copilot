"""
Token cost calculator for Anthropic Claude models.
Based on published pricing (as of Feb 2025).
"""

# Anthropic Claude pricing (USD per 1M tokens)
PRICING = {
    "claude-haiku-4-5-20251001": {
        "input": 0.80,
        "output": 4.00,
    },
    "claude-sonnet-5": {
        "input": 3.00,
        "output": 15.00,
    },
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """
    Calculate USD cost for a single LLM call.
    Args:
        model: Model name (e.g., "claude-haiku-4-5-20251001")
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
    Returns:
        Cost in USD
    """
    if model not in PRICING:
        # Fallback: assume Haiku pricing if unknown
        pricing = PRICING["claude-haiku-4-5-20251001"]
    else:
        pricing = PRICING[model]

    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]

    return input_cost + output_cost


if __name__ == "__main__":
    # Example usage
    cost = calculate_cost("claude-haiku-4-5-20251001", 500, 150)
    print(f"Haiku (500 in, 150 out): ${cost:.6f}")

    cost = calculate_cost("claude-sonnet-5", 500, 150)
    print(f"Sonnet (500 in, 150 out): ${cost:.6f}")
