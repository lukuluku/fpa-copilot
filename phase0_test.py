#!/usr/bin/env python
"""
Phase 0: Minimal skeleton to verify API key and environment setup.
Sends one hardcoded finance question to Claude and prints the response.
No agents, retrieval, or orchestration yet — just end-to-end LLM call.
"""

import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

def main():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not found in .env file")
        print("Please create a .env file with: ANTHROPIC_API_KEY=your-key-here")
        return

    client = Anthropic()

    query = "How would you approach analyzing a 15% unfavorable variance in Q3 operating expenses?"

    print("=" * 70)
    print("PHASE 0: Environment & API Verification")
    print("=" * 70)
    print(f"\nQuery: {query}\n")

    try:
        message = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": query,
                }
            ],
        )

        response_text = message.content[0].text
        print("Response:")
        print("-" * 70)
        print(response_text)
        print("-" * 70)
        print(f"\nSuccess! API key is valid and connected.")
        print(f"Model: {message.model}")
        print(f"Stop reason: {message.stop_reason}")

    except Exception as e:
        print(f"ERROR: {e}")
        print("\nCheck your API key in .env and ensure it's valid.")


if __name__ == "__main__":
    main()
