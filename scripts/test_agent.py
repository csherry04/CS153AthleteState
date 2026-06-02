#!/usr/bin/env python3
"""Test the coaching agent with OpenRouter."""

import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("✗ OPENROUTER_API_KEY is not set")
        sys.exit(1)

    os.environ["OPENROUTER_API_KEY"] = api_key

    from src.agent_tools import CoachingAgentTools

    tools = CoachingAgentTools()
    print("✓ Tools initialized\n")

    print("Test 1: get_day('2026-05-15')")
    day = tools.get_day("2026-05-15")
    print(f"  Score: {day.get('combined_score')} ({day.get('combined_level')})")
    print(f"  Alert: {day.get('alert_label')}")
    print(f"  7d volume: {day.get('run_7d_km')} km\n")

    print("Test 2: compare_days('2024-03-15', '2026-05-15')")
    comp = tools.compare_days("2024-03-15", "2026-05-15")
    print(f"  Score change: {comp.get('score_change')} points")
    print(f"  Volume change: {comp.get('run_7d_change_km')} km\n")

    print("Test 3: get_frontier_evaluation()")
    frontier = tools.get_frontier_evaluation()
    print(f"  Title: {frontier.get('title')}")
    print(f"  Key finding: {frontier.get('key_finding')}\n")

    print("✓ All tool tests passed!")
    print("\nNow try the interactive agent:")
    print("  export OPENROUTER_API_KEY='sk-or-...'\n  python scripts/run_coaching_agent.py")


if __name__ == "__main__":
    main()
