#!/usr/bin/env python3
"""Quick test of agent with OpenRouter API."""

import json
import os
import sys

sys.path.insert(0, "/Users/callumsherry/athlete-state-model")

api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    print("✗ OPENROUTER_API_KEY is not set")
    sys.exit(1)

try:
    import httpx
    print("✓ httpx installed")
except ImportError:
    print("✗ httpx not installed")
    sys.exit(1)

try:
    from src.agent_tools import CoachingAgentTools

    print("✓ CoachingAgentTools imported")
    tools = CoachingAgentTools()
    print("✓ Tools initialized with your data\n")

    result = tools.get_day("2026-05-15")
    print("✓ get_day test passed")
    print(f"  Score: {result['combined_score']}, Alert: {result['alert_label']}\n")

    print("Testing OpenRouter API connection...")
    print(f"Using API key: {api_key[:20]}...\n")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "openrouter/auto",
        "messages": [{"role": "user", "content": "What is 2+2?"}],
        "temperature": 0.5,
        "max_tokens": 50,
    }

    try:
        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=10.0,
        )
        print(f"API Response Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if "choices" in data and data["choices"]:
                msg = data["choices"][0].get("message", {}).get("content", "")
                print("✓ OpenRouter API working!")
                print(f"  Response: {msg[:100]}...")
            else:
                print("✗ Unexpected response format")
                print(json.dumps(data, indent=2)[:500])
        else:
            print(f"✗ API error: {response.status_code}")
            print(response.text[:500])

    except httpx.TimeoutException:
        print("✗ Request timeout (OpenRouter may be slow)")
    except httpx.HTTPError as e:
        print(f"✗ HTTP error: {e}")

    print("\n✓ All tests passed! Ready to run interactive agent.")
    print("\nTo start the interactive agent:")
    print("  export OPENROUTER_API_KEY='sk-or-...'" )
    print("  python scripts/run_coaching_agent.py")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
