#!/usr/bin/env python3
"""Coaching agent: Q&A with tool grounding.

Usage:
    python scripts/run_coaching_agent.py
    
Then ask questions like:
    > Why was May 15 flagged at 72 km when I've done 140 km weeks?
    > How did my bone stress change between spring 2024 and now?
    > What if I'd cut volume by 15% on my peak risk days?
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.agent_tools import CoachingAgentTools

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Install with: pip install httpx")
    sys.exit(1)


class CoachingAgent:
    """Agent that calls an LLM with tool grounding."""

    def __init__(self, api_key: str | None = None):
        """Initialize agent credentials."""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set. Pass as argument or set env var.")

        self.tools = CoachingAgentTools()
        self.model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        self.base_url = "https://api.openai.com/v1"
        self.max_turns = 5

    def run_interactive(self):
        """Run an interactive REPL for Q&A."""
        print("\n=== Coaching Agent (Frontier Monitoring) ===")
        print("Ask questions about your training, monitoring, and bone-stress risk.")
        print("Type 'quit' to exit.\n")

        messages: list[dict[str, Any]] = []
        system_prompt = self._build_system_prompt()

        while True:
            try:
                user_input = input("You: ").strip()
            except EOFError:
                break
            except KeyboardInterrupt:
                print("\nExiting.")
                break

            if user_input.lower() in ("quit", "exit"):
                break

            if not user_input:
                continue

            messages.append({"role": "user", "content": user_input})

            # Agent loop: call LLM, check for tool calls, execute, loop
            response = self._agentic_loop(system_prompt, messages)
            if response:
                messages.append({"role": "assistant", "content": response})
                print(f"\nAgent: {response}\n")

    def _build_system_prompt(self) -> str:
        """Build the system prompt with context and tool definitions."""
        return f"""You are a coaching AI for an athlete's personal monitoring lab.

You have access to 7 years of daily monitoring data (Garmin, training logs) and three parallel bone-stress tracking systems:
- Literature-based (industry standards)
- Personalized (learned from this athlete's patterns)
- Frontier (combines anomaly detection + injury-aware embedding similarity)

Your role:
1. Answer questions about specific days, comparisons, and patterns.
2. Use tools to ground every answer in actual data.
3. Provide actionable insights backed by the monitoring data.
4. Be honest about model limitations and heuristics.

Key context:
- The athlete sustained a bone stress injury in spring 2024 (used for validation).
- Recent volume: typically 100-140 km/week.
- Last review: May 15, 2026.
- Data spans Aug 2018 – May 2026.

When answering:
- Call tools to retrieve data.
- Quote specific dates, scores, and metrics.
- Acknowledge model agreement/disagreement if relevant.
- For what-if scenarios, note that estimates are heuristic-based.

Response style:
- Plain text only (no markdown, no headings, no asterisks).
- 4 to 8 sentences.
- If listing items, use "1)" "2)" formatting.

Tool descriptions:
{json.dumps(self.tools.list_tool_descriptions(), indent=2)}

When you need data, call the appropriate tool."""

    def _agentic_loop(self, system_prompt: str, messages: list[dict[str, Any]]) -> str | None:
        """Run the agentic loop: LLM -> tool calls -> tool results -> LLM response."""
        for turn in range(self.max_turns):
            response = self._call_model(system_prompt, messages)

            if response is None:
                return None

            content = response.get("content") or ""
            tool_calls = self._extract_tool_calls(content, response.get("tool_calls"))

            if not tool_calls:
                return content

            # Add assistant message with tool calls to keep proper tool_call_id linkage
            assistant_tool_calls = []
            for tool_call in tool_calls:
                assistant_tool_calls.append(
                    {
                        "id": tool_call["id"],
                        "type": "function",
                        "function": {
                            "name": tool_call["name"],
                            "arguments": json.dumps(tool_call["args"]),
                        },
                    }
                )

            messages.append(
                {
                    "role": "assistant",
                    "content": content if content else None,
                    "tool_calls": assistant_tool_calls,
                }
            )

            # Execute tools and add tool results
            for tool_call in tool_calls:
                result = self._execute_tool(tool_call["name"], tool_call["args"])
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": json.dumps(result),
                    }
                )

        return content

    def _call_model(self, system_prompt: str, messages: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Call the chat completions API with tool calling."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        tools = [{"type": "function", "function": tool} for tool in self.tools.list_tool_descriptions()]

        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system_prompt}] + messages,
            "tools": tools,
            "tool_choice": "auto",
            "temperature": 0.7,
            "max_tokens": 1024,
        }

        try:
            response = httpx.post(f"{self.base_url}/chat/completions", json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            data = response.json()

            # Extract content or function call
            if "choices" not in data or not data["choices"]:
                print(f"ERROR: Unexpected response format: {data}")
                return None

            choice = data["choices"][0]
            if "message" not in choice:
                return None

            msg = choice["message"]
            return {
                "content": msg.get("content", ""),
                "tool_calls": msg.get("tool_calls", []),
            }

        except httpx.HTTPError as e:
            print(f"ERROR calling API: {e}")
            return None

    def _extract_tool_calls(self, content: str, tool_calls: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        """Normalize tool calls from API or XML-like tool tags.

        Returns a list of dicts: {"id": str, "name": str, "args": dict}
        """
        normalized: list[dict[str, Any]] = []

        # Primary: API tool_calls
        if tool_calls:
            for tool_call in tool_calls:
                function = tool_call.get("function", tool_call)
                name = function.get("name")
                args = function.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                if name:
                    normalized.append({"id": tool_call.get("id", str(uuid4())), "name": name, "args": args})

        if normalized:
            return normalized

        # Fallback: XML-like tool tags in content
        content = (content or "").strip()
        if not content:
            return []

        import re

        for xml_match in re.finditer(r'<tool_call\s+name=["\']([^"\']+)["\']\s*>(.*?)</tool_call>', content, re.DOTALL):
            tool_name = xml_match.group(1).strip()
            body = xml_match.group(2)
            tool_args: dict[str, Any] = {}

            param_matches = re.findall(r'<param\s+name=["\']([^"\']+)["\']\s*>(.*?)</param>', body, re.DOTALL)
            for param_name, param_value in param_matches:
                cleaned_value = param_value.strip()
                try:
                    tool_args[param_name] = json.loads(cleaned_value)
                except json.JSONDecodeError:
                    tool_args[param_name] = cleaned_value

            if tool_name:
                normalized.append({"id": str(uuid4()), "name": tool_name, "args": tool_args})

        return normalized

    def _execute_tool(self, tool_name: str, tool_args: dict) -> Any:
        """Execute a tool by name and args."""
        if tool_name == "get_day":
            return self.tools.get_day(tool_args.get("date_str", ""))
        elif tool_name == "compare_days":
            return self.tools.compare_days(tool_args.get("date1_str", ""), tool_args.get("date2_str", ""))
        elif tool_name == "get_periods_around":
            return self.tools.get_periods_around(
                tool_args.get("date_str", ""),
                lookback_days=tool_args.get("lookback_days", 7),
                lookahead_days=tool_args.get("lookahead_days", 7),
            )
        elif tool_name == "simulate_volume_cut":
            return self.tools.simulate_volume_cut(tool_args.get("date_str", ""), factor=tool_args.get("factor", 0.85))
        elif tool_name == "get_frontier_evaluation":
            return self.tools.get_frontier_evaluation()
        elif tool_name == "get_riskiest_period":
            return self.tools.get_riskiest_period(tool_args.get("metric", "peak_accumulated_bone_stress_state"))
        elif tool_name == "get_highlighted_days":
            return self.tools.get_highlighted_days(
                start_date=tool_args.get("start_date", "2024-02-01"),
                end_date=tool_args.get("end_date", "2024-04-01"),
                top_n=tool_args.get("top_n", 8),
            )
        elif tool_name == "explain_day_flag":
            return self.tools.explain_day_flag(
                date_str=tool_args.get("date_str", ""),
                model=tool_args.get("model", "frontier"),
            )
        elif tool_name == "analyze_progression":
            return self.tools.analyze_progression(
                end_date=tool_args.get("end_date", ""),
                lookback_days=tool_args.get("lookback_days", 42),
                reference_weekly_increase_pct=tool_args.get("reference_weekly_increase_pct", 10.0),
            )
        elif tool_name == "get_athlete_profile_insights":
            return self.tools.get_athlete_profile_insights()
        elif tool_name == "compare_periods":
            return self.tools.compare_periods(
                tool_args.get("start_a", ""),
                tool_args.get("end_a", ""),
                tool_args.get("start_b", ""),
                tool_args.get("end_b", ""),
            )
        elif tool_name == "get_recent_trend":
            return self.tools.get_recent_trend(tool_args.get("days", 30))
        elif tool_name == "analyze_workout":
            return self.tools.analyze_workout(tool_args.get("date_str", ""))
        elif tool_name == "analyze_recovery_context":
            return self.tools.analyze_recovery_context(tool_args.get("date_str", ""))
        elif tool_name == "explain_model_disagreement":
            return self.tools.explain_model_disagreement(tool_args.get("date_str", ""))
        elif tool_name == "suggest_training_adjustment":
            return self.tools.suggest_training_adjustment(tool_args.get("date_str"))
        elif tool_name == "simulate_adjustment_plan":
            return self.tools.simulate_adjustment_plan(
                date_str=tool_args.get("date_str", ""),
                target_literature_score=tool_args.get("target_literature_score", 70.0),
                min_factor=tool_args.get("min_factor", 0.5),
            )
        elif tool_name == "investigate_training_state":
            return self.tools.investigate_training_state(
                date_str=tool_args.get("date_str"),
                lookback_days=tool_args.get("lookback_days", 42),
            )
        else:
            return {"error": f"Unknown tool: {tool_name}"}


def demo_mode():
    """Run a demo with pre-defined questions (no API key needed)."""
    print("\n=== Demo Mode (no API calls) ===\n")
    tools = CoachingAgentTools()

    # Three killer questions
    questions = [
        ("Why was May 15 flagged at 72 km when I've done 140 km weeks?", "compare_days", ["2026-05-15", "2024-01-18"]),
        ("How did my bone stress change between spring 2024 and now?", "compare_days", ["2024-03-15", "2026-05-15"]),
        ("What if I'd cut volume by 15% on my peak risk days?", "simulate_volume_cut", ["2024-03-01"]),
    ]

    for q, tool_type, params in questions:
        print(f"Q: {q}")
        result = None
        if tool_type == "compare_days":
            result = tools.compare_days(params[0], params[1])
            print(f"Tool: compare_days({params[0]}, {params[1]})")
        elif tool_type == "get_day":
            result = tools.get_day(params[0])
            print(f"Tool: get_day({params[0]})")
        elif tool_type == "simulate_volume_cut":
            result = tools.simulate_volume_cut(params[0], factor=0.85)
            print(f"Tool: simulate_volume_cut({params[0]}, 0.85)")

        if result:
            print(f"Result: {json.dumps(result, indent=2)}")
        print()


def main():
    """Entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        demo_mode()
        return

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found.")
        print("Set it with: export OPENAI_API_KEY=your_key_here")
        print("Or run with --demo flag to see example tool calls without API.")
        sys.exit(1)

    agent = CoachingAgent(api_key=api_key)
    agent.run_interactive()


if __name__ == "__main__":
    main()
