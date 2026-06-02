"""FastAPI backend for the coaching agent (OpenRouter + tool calls)."""

from __future__ import annotations

import json
import os
import re
from typing import Any
from uuid import uuid4

import httpx
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.agent_tools import CoachingAgentTools


class CoachRequest(BaseModel):
    message: str
    history: list[dict[str, str]] | None = None


class CoachResponse(BaseModel):
    reply: str
    tool_results: list[dict[str, Any]] | None = None


app = FastAPI(title="Athlete State Coach API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"] ,
    allow_headers=["*"],
)

TOOLS = CoachingAgentTools()


def _system_prompt(tools: CoachingAgentTools) -> str:
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

Critical accuracy rules:
- If the user asks to investigate a day/state, produce a case file, evaluate risk, explain a flagged day deeply, or asks for what to do next from a specific state, call investigate_training_state.
- If the user asks how much to cut, what reduction would matter, or asks for a simulation/planner, call simulate_adjustment_plan or simulate_down_week_impact.
- If the user asks why a specific day was flagged, call explain_day_flag.
- If the user asks what days were highlighted/flagged by models, call get_highlighted_days.
- Never say ACWR directly caused a frontier flag. ACWR is literature/workload-rule context unless frontier attribution explicitly says otherwise.
- For frontier explanations, distinguish direct frontier evidence (novelty, forecast error, reference similarity, attribution/neighbors) from contextual workload facts (volume, ACWR, accumulated state).
- If exact frontier feature causality is not stored, say so plainly and give the strongest available contextual interpretation.
- Do not claim a weekly mileage range is "safe." Use phrases like "more conservative," "lower-risk relative to this ramp," or "historically better tolerated" only when supported by tool data.
- If the user asks how steep a progression was or what it should have been, call analyze_progression and compare actual week-to-week changes against the stated reference benchmark.
- If the user asks about weaknesses, strengths, training structure, or general advice, call get_athlete_profile_insights and suggest_training_adjustment.
- If the user asks whether recovery contributed, call analyze_recovery_context.
- If the user asks why models disagree, call explain_model_disagreement.
- If the user asks about a workout or session on a day, call analyze_workout.
- If the user compares blocks or cycles, call compare_periods.

Key context:
- The athlete sustained a bone stress injury in spring 2024 (used for validation).
- Recent volume: typically 100-140 km/week.
- Last review: May 15, 2026.
- Data spans Aug 2018 – May 2026.

Tool descriptions:
{json.dumps(tools.list_tool_descriptions(), indent=2)}

Response style:
- Use plain text only (no markdown, no headings, no asterisks).
- Prefer short paragraphs over long numbered blocks.
- Keep answers concise: 2 to 4 short paragraphs.
- Use bullets only when the user explicitly asks for a list.
- Always ground answers in tool data and mention specific dates or scores.

When you need data, call the appropriate tool."""


def _clean_response(text: str) -> str:
    if not text:
        return text

    text = re.sub(r"<\/?(?:antml|tml|function_calls|invoke|parameter|tool_call|function)[^>]*>", "", text)
    text = re.sub(r"\b(?:antml|tml|function_calls|invoke|parameter|tool_call|function)\b", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    cleaned = re.sub(r"^\s*#+\s*", "", text, flags=re.MULTILINE)
    cleaned = re.sub(r"\*\*|\*|__|`", "", cleaned)
    cleaned = re.sub(r"[_<>]+", " ", cleaned)
    cleaned = re.sub(r"\s+([,.?:;])", r"\1", cleaned)
    cleaned = re.sub(r"\b(\w+)\s+\1\b", r"\1", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _looks_like_tool_garble(text: str) -> bool:
    lowered = (text or "").lower()
    markers = ["<tool_call", "antml", "tml:", "function_calls", "invoke name", "parameter name"]
    return any(marker in lowered for marker in markers)


def _infer_date_from_message(message: str) -> str | None:
    explicit = re.search(r"20\d{2}-\d{2}-\d{2}", message)
    if explicit:
        return explicit.group(0)
    lowered = message.lower()
    if "feb" in lowered and ("9" in lowered or "ninth" in lowered):
        return "2024-02-09"
    if "may 15" in lowered or "current" in lowered or "latest" in lowered:
        return str(TOOLS.scores_df["date"].max().date())
    return None


def _prefetch_tools(message: str) -> list[dict[str, Any]]:
    """Run obvious tool calls before the LLM to reduce malformed tool chatter."""
    lowered = message.lower()
    calls: list[dict[str, Any]] = []

    if "advice" in lowered or "structure my training" in lowered or "risk history" in lowered:
        profile = TOOLS.get_athlete_profile_insights()
        adjustment = TOOLS.suggest_training_adjustment()
        calls.extend(
            [
                {"tool": "get_athlete_profile_insights", "args": {}, "result": profile},
                {"tool": "suggest_training_adjustment", "args": {}, "result": adjustment},
            ]
        )

    if "investigate" in lowered or "case file" in lowered or "what should i do" in lowered or "what to do" in lowered:
        date = _infer_date_from_message(message) or str(TOOLS.scores_df["date"].max().date())
        calls.append({"tool": "investigate_training_state", "args": {"date_str": date, "lookback_days": 42}, "result": TOOLS.investigate_training_state(date, 42)})

    if "how much" in lowered and ("cut" in lowered or "reduce" in lowered or "lower" in lowered):
        date = _infer_date_from_message(message) or str(TOOLS.scores_df["date"].max().date())
        calls.append({"tool": "simulate_adjustment_plan", "args": {"date_str": date}, "result": TOOLS.simulate_adjustment_plan(date)})

    if "weakness" in lowered or "strength" in lowered or "pattern" in lowered:
        calls.append({"tool": "get_athlete_profile_insights", "args": {}, "result": TOOLS.get_athlete_profile_insights()})

    if ("highlight" in lowered or "flag" in lowered) and ("last month" in lowered or "recent" in lowered):
        latest = TOOLS.scores_df["date"].max()
        start = (latest - pd.Timedelta(days=30)).strftime("%Y-%m-%d")
        end = latest.strftime("%Y-%m-%d")
        calls.append(
            {
                "tool": "get_highlighted_days",
                "args": {"start_date": start, "end_date": end, "top_n": 5},
                "result": TOOLS.get_highlighted_days(start_date=start, end_date=end, top_n=5),
            }
        )

    if "why" in lowered and ("flag" in lowered or "frontier" in lowered or "literature" in lowered or "personalized" in lowered):
        date = _infer_date_from_message(message)
        if date:
            model = "frontier" if "frontier" in lowered else "literature" if "literature" in lowered else "personalized" if "personalized" in lowered else "all"
            calls.append(
                {
                    "tool": "explain_day_flag",
                    "args": {"date_str": date, "model": model},
                    "result": TOOLS.explain_day_flag(date_str=date, model=model),
                }
            )

    if "progression" in lowered or "how fast" in lowered or "steep" in lowered or "increasing" in lowered:
        date = _infer_date_from_message(message) or str(TOOLS.scores_df["date"].max().date())
        calls.append(
            {
                "tool": "analyze_progression",
                "args": {"end_date": date, "lookback_days": 42, "reference_weekly_increase_pct": 10.0},
                "result": TOOLS.analyze_progression(end_date=date, lookback_days=42, reference_weekly_increase_pct=10.0),
            }
        )

    if "recovery" in lowered or "hrv" in lowered or "readiness" in lowered or "sleep" in lowered:
        date = _infer_date_from_message(message) or str(TOOLS.scores_df["date"].max().date())
        calls.append({"tool": "analyze_recovery_context", "args": {"date_str": date}, "result": TOOLS.analyze_recovery_context(date)})

    if "disagree" in lowered or "disagreement" in lowered or "why do the models" in lowered:
        date = _infer_date_from_message(message) or str(TOOLS.scores_df["date"].max().date())
        calls.append({"tool": "explain_model_disagreement", "args": {"date_str": date}, "result": TOOLS.explain_model_disagreement(date)})

    if "workout" in lowered or "session" in lowered or "run on" in lowered:
        date = _infer_date_from_message(message)
        if date:
            calls.append({"tool": "analyze_workout", "args": {"date_str": date}, "result": TOOLS.analyze_workout(date)})

    if "trend" in lowered or "trending" in lowered or "last 30" in lowered or "recent" in lowered:
        calls.append({"tool": "get_recent_trend", "args": {"days": 30}, "result": TOOLS.get_recent_trend(30)})

    return calls


def _format_day_scores(date_str: str, day: dict[str, Any]) -> str:
    return (
        f"On {date_str}, the system read as {day.get('alert_label')} / {day.get('combined_level')} "
        f"with integrated score {day.get('integrated_score', day.get('combined_score'))}. "
        f"Literature was {day.get('literature_score')}, personalized was {day.get('personalized_score')}, "
        f"and frontier strain was {day.get('frontier_score')}. "
        f"The main reason was {day.get('reason')}, with {day.get('run_7d_km')} km over 7 days and "
        f"accumulated state {day.get('accumulated_state')}."
    )


def _answer_spring_2024_scores() -> tuple[str, list[dict[str, Any]]]:
    dates = ["2024-02-05", "2024-02-09", "2024-02-10", "2024-03-12", "2024-03-15"]
    days = [TOOLS.get_day(date) for date in dates]
    tool_results = [{"tool": "get_day", "args": {"date_str": date}, "result": day} for date, day in zip(dates, days)]
    eval_data = TOOLS.get_frontier_evaluation()
    tool_results.append({"tool": "get_frontier_evaluation", "args": {}, "result": eval_data})

    feb5, feb9, feb10, mar12, mar15 = days
    reply = (
        "Heading into the spring 2024 bone-stress injury, all three tracks were already elevated weeks before the main March risk block.\n\n"
        f"1) First high signal: on 2024-02-05, literature was {feb5.get('literature_score')}, personalized was {feb5.get('personalized_score')}, "
        f"frontier was {feb5.get('frontier_score')}, and the integrated score was {feb5.get('integrated_score')}.\n"
        f"2) Frontier confirmation: on 2024-02-09, frontier strain was {feb9.get('frontier_score')}, with integrated score {feb9.get('integrated_score')} and {feb9.get('run_7d_km')} km over 7 days.\n"
        f"3) All-track agreement: by 2024-02-10, the alert was {feb10.get('alert_label')} and agreement was {feb10.get('agreement')}.\n"
        f"4) Peak March block: on 2024-03-12, literature was {mar12.get('literature_score')}, personalized was {mar12.get('personalized_score')}, frontier was {mar12.get('frontier_score')}, and integrated score was {mar12.get('integrated_score')}.\n"
        f"5) By 2024-03-15, integrated score was {mar15.get('integrated_score')} with {mar15.get('run_7d_km')} km over 7 days.\n\n"
        "Bottom line: literature and personalized went high first, frontier joined within days, and all three were aligned about 51 days before the injury evaluation endpoint."
    )
    return reply, tool_results


def _answer_riskiest_period() -> tuple[str, list[dict[str, Any]]]:
    period = TOOLS.get_riskiest_period()
    tool_results = [{"tool": "get_riskiest_period", "args": {}, "result": period}]
    reply = (
        f"Your riskiest historical period was {period.get('start_date')} to {period.get('end_date')}.\n\n"
        f"It lasted {period.get('calendar_days')} calendar days, with {period.get('elevated_days')} elevated days. "
        f"The accumulated bone-stress state peaked at {period.get('peak_state')}, the mean state was {period.get('mean_state')}, "
        f"and peak 7-day running volume reached {period.get('peak_7d_km')} km.\n\n"
        f"The dominant pattern was {period.get('dominant_reason')}. "
        f"This is the clearest high-risk block because it combined duration, high accumulated state, and sustained running load rather than a single isolated spike."
    )
    return reply, tool_results


def _answer_current_risk() -> tuple[str, list[dict[str, Any]]]:
    latest = str(TOOLS.scores_df["date"].max().date())
    day = TOOLS.get_day(latest)
    return _format_day_scores(latest, day), [{"tool": "get_day", "args": {"date_str": latest}, "result": day}]


def _answer_feb_2024_down_week() -> tuple[str, list[dict[str, Any]]]:
    scenario = TOOLS.simulate_down_week_impact(start_date="2024-02-05", factor=0.8, days=7)
    eval_data = TOOLS.get_frontier_evaluation()
    tool_results = [
        {"tool": "simulate_down_week_impact", "args": {"start_date": "2024-02-05", "factor": 0.8, "days": 7}, "result": scenario},
        {"tool": "get_frontier_evaluation", "args": {}, "result": eval_data},
    ]

    days = scenario.get("days", [])
    peak_day = max(days, key=lambda row: row.get("actual_integrated_score") or 0) if days else {}
    actual_range = scenario.get("actual_integrated_range")
    literature_range = scenario.get("actual_literature_range")
    scenario_range = scenario.get("scenario_literature_range")
    mean_delta = scenario.get("mean_literature_delta")
    largest_drop = scenario.get("largest_literature_drop")

    reply = (
        "You were right to question the earlier answer: the real February 2024 scores were much higher than the 49-point baseline it quoted.\n\n"
        f"For the Feb 5 to Feb 11, 2024 window, your actual integrated score ranged from {actual_range[0]} to {actual_range[1]}. "
        f"The peak day in that window was {peak_day.get('date')}, with integrated {peak_day.get('actual_integrated_score')}, "
        f"literature {peak_day.get('actual_literature_score')}, personalized {peak_day.get('actual_personalized_score')}, "
        f"frontier {peak_day.get('actual_frontier_score')}, and {peak_day.get('actual_run7_km')} km over 7 days.\n\n"
        f"If you inserted a 20% lower down week starting Feb 5, the recomputed literature workload score would range from {scenario_range[0]} to {scenario_range[1]} "
        f"instead of the actual literature range of {literature_range[0]} to {literature_range[1]}. "
        f"Across the week, that is an average literature-score change of {mean_delta} points, with the biggest single-day drop about {abs(largest_drop)} points.\n\n"
        "Important caveat: this is not a full injury-counterfactual. It recomputes the workload/literature score from lower volume, but it does not fully rerun the frontier embeddings, personalized percentile history, or accumulated tissue-state dynamics. "
        "So the truthful read is: a 20% down week likely would have reduced the load-rule score by a few points, but the major value would have been interrupting the sustained high-load trajectory before the March block, not magically turning an 80+ risk state into low risk in one week."
    )
    return reply, tool_results


def _answer_highlighted_days_all_models() -> tuple[str, list[dict[str, Any]]]:
    highlights = TOOLS.get_highlighted_days(start_date="2024-02-01", end_date="2024-04-01", top_n=5)
    tool_results = [
        {
            "tool": "get_highlighted_days",
            "args": {"start_date": "2024-02-01", "end_date": "2024-04-01", "top_n": 5},
            "result": highlights,
        }
    ]

    def line(model: str, title: str) -> str:
        rows = highlights.get(model, [])[:5]
        items = []
        for row in rows:
            reason = row.get("reason") or "model-specific high strain"
            items.append(
                f"{row.get('date')} score {row.get('score')} ({row.get('run_7d_km')} km 7d, {reason})"
            )
        return f"{title}: " + "; ".join(items) + "."

    reply = (
        "For the spring 2024 injury window, the three models highlighted overlapping but not identical days.\n\n"
        f"1) {line('literature', 'Literature / workload rules')}\n\n"
        f"2) {line('personalized', 'Personalized / your-history model')}\n\n"
        f"3) {line('frontier', 'Frontier / learned-state model')}\n\n"
        "How to read this: literature is flagging objective load-rule stress, personalized is flagging load that is unusual relative to your own history, and frontier is flagging multivariate learned-state strain. "
        "The days that matter most are the overlaps, because agreement means the system was seeing both high mechanical load and an unusual/strained athlete state."
    )
    return reply, tool_results


def _answer_frontier_day_why(date_str: str = "2024-02-09") -> tuple[str, list[dict[str, Any]]]:
    day = TOOLS.get_day(date_str)
    tool_results = [{"tool": "get_day", "args": {"date_str": date_str}, "result": day}]

    frontier_parts = []
    if day.get("embedding_novelty_score") is not None:
        frontier_parts.append(f"embedding novelty {day.get('embedding_novelty_score')}")
    if day.get("contrastive_novelty_score") is not None:
        frontier_parts.append(f"contrastive novelty {day.get('contrastive_novelty_score')}")
    if day.get("readiness_forecast_error_score") is not None:
        frontier_parts.append(f"readiness forecast error {day.get('readiness_forecast_error_score')}")
    if day.get("reference_similarity_score") is not None:
        frontier_parts.append(f"reference similarity score {day.get('reference_similarity_score')}")

    components_text = ", ".join(frontier_parts) if frontier_parts else "the stored frontier component scores are not available for this day"
    attribution = day.get("attribution") or day.get("attribution_drivers") or "no stable attribution text was stored for this day"
    neighbors = day.get("neighbors") or "no nearest-neighbor summary was stored for this day"

    reply = (
        f"For {date_str}, the frontier model flagged the day because its learned-state strain score was high: frontier {day.get('frontier_score')}, integrated {day.get('integrated_score')}.\n\n"
        f"The frontier-specific components available for that day are: {components_text}. "
        f"The stored attribution/neighborhood context says: {attribution}. Similar-day context: {neighbors}.\n\n"
        f"The workload facts around the day were {day.get('run_7d_km')} km over 7 days, {day.get('run_28d_km')} km over 28 days, and accumulated bone-stress state {day.get('accumulated_state')}. "
        "Those workload facts help interpret the flag, but they are not the frontier model itself. ACWR belongs to the literature/workload-rule track, so it should be treated as context, not as the direct reason the frontier model fired.\n\n"
        "Most accurate wording: the frontier model highlighted this day as a high learned-state strain/anomaly day that coincided with a sustained high-volume load block. We can give contributing context, but we should not claim exact causal feature importance unless the stored frontier attribution exists for that day."
    )
    return reply, tool_results


def _local_fast_answer(message: str) -> tuple[str, list[dict[str, Any]]] | None:
    normalized = message.lower()
    if os.getenv("COACH_FAST_PATHS", "0") != "1":
        return None
    if ("feb" in normalized or "february" in normalized) and ("down week" in normalized or "20%" in normalized or "lower" in normalized):
        return _answer_feb_2024_down_week()
    if "current" in normalized and "risk" in normalized:
        return _answer_current_risk()
    return None


def _extract_tool_calls(content: str, tool_calls: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []

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


def _execute_tool(name: str, args: dict[str, Any]) -> Any:
    if name == "get_day":
        return TOOLS.get_day(args.get("date_str", ""))
    if name == "compare_days":
        return TOOLS.compare_days(args.get("date1_str", ""), args.get("date2_str", ""))
    if name == "get_periods_around":
        return TOOLS.get_periods_around(
            args.get("date_str", ""),
            lookback_days=args.get("lookback_days", 7),
            lookahead_days=args.get("lookahead_days", 7),
        )
    if name == "simulate_volume_cut":
        return TOOLS.simulate_volume_cut(args.get("date_str", ""), factor=args.get("factor", 0.85))
    if name == "simulate_down_week_impact":
        return TOOLS.simulate_down_week_impact(
            start_date=args.get("start_date", "2024-02-05"),
            factor=args.get("factor", 0.8),
            days=args.get("days", 7),
        )
    if name == "get_frontier_evaluation":
        return TOOLS.get_frontier_evaluation()
    if name == "get_riskiest_period":
        return TOOLS.get_riskiest_period(args.get("metric", "peak_accumulated_bone_stress_state"))
    if name == "get_highlighted_days":
        return TOOLS.get_highlighted_days(
            start_date=args.get("start_date", "2024-02-01"),
            end_date=args.get("end_date", "2024-04-01"),
            top_n=args.get("top_n", 8),
        )
    if name == "explain_day_flag":
        return TOOLS.explain_day_flag(
            date_str=args.get("date_str", ""),
            model=args.get("model", "frontier"),
        )
    if name == "analyze_progression":
        return TOOLS.analyze_progression(
            end_date=args.get("end_date", ""),
            lookback_days=args.get("lookback_days", 42),
            reference_weekly_increase_pct=args.get("reference_weekly_increase_pct", 10.0),
        )
    if name == "get_athlete_profile_insights":
        return TOOLS.get_athlete_profile_insights()
    if name == "compare_periods":
        return TOOLS.compare_periods(args.get("start_a", ""), args.get("end_a", ""), args.get("start_b", ""), args.get("end_b", ""))
    if name == "get_recent_trend":
        return TOOLS.get_recent_trend(args.get("days", 30))
    if name == "analyze_workout":
        return TOOLS.analyze_workout(args.get("date_str", ""))
    if name == "analyze_recovery_context":
        return TOOLS.analyze_recovery_context(args.get("date_str", ""))
    if name == "explain_model_disagreement":
        return TOOLS.explain_model_disagreement(args.get("date_str", ""))
    if name == "suggest_training_adjustment":
        return TOOLS.suggest_training_adjustment(args.get("date_str"))
    if name == "simulate_adjustment_plan":
        return TOOLS.simulate_adjustment_plan(
            date_str=args.get("date_str", ""),
            target_literature_score=args.get("target_literature_score", 70.0),
            min_factor=args.get("min_factor", 0.5),
        )
    if name == "investigate_training_state":
        return TOOLS.investigate_training_state(
            date_str=args.get("date_str"),
            lookback_days=args.get("lookback_days", 42),
        )
    return {"error": f"Unknown tool: {name}"}


def run_agentic_query(message: str, history: list[dict[str, str]] | None = None, max_turns: int = 3) -> tuple[str, list[dict[str, Any]]]:
    fast_answer = _local_fast_answer(message)
    if fast_answer:
        return fast_answer

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="OPENROUTER_API_KEY not set on server")

    model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-haiku")

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    tools_payload = [{"type": "function", "function": tool} for tool in TOOLS.list_tool_descriptions()]

    prefetched_results = _prefetch_tools(message)

    messages = [{"role": "system", "content": _system_prompt(TOOLS)}]
    if history:
        for item in history[-4:]:
            role = item.get("role", "user")
            content = item.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": message})

    if prefetched_results:
        messages.append(
            {
                "role": "user",
                "content": (
                    "The following tool results have already been retrieved. Answer using these results. "
                    "Do not emit tool calls or tool markup.\n"
                    f"{json.dumps({'tool_results': prefetched_results}, default=str)}"
                ),
            }
        )

    tool_results_log: list[dict[str, Any]] = list(prefetched_results)

    for _ in range(max_turns):
        payload = {
            "model": model,
            "messages": messages,
            "tools": tools_payload,
            "tool_choice": "auto",
            "temperature": 0.2,
            "max_tokens": 600,
        }

        response = httpx.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=30.0)
        response.raise_for_status()
        data = response.json()

        if not data.get("choices"):
            raise HTTPException(status_code=500, detail="OpenRouter returned no choices")

        msg = data["choices"][0].get("message", {})
        content = msg.get("content", "")
        tool_calls = _extract_tool_calls(content, msg.get("tool_calls"))

        if not tool_calls:
            cleaned = _clean_response(content)
            if _looks_like_tool_garble(content) and tool_results_log:
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Your previous draft contained tool-call markup or malformed tool syntax. "
                            "Rewrite the answer in clean plain English using only the tool results already provided. "
                            "Do not include any XML, tags, function names, or hidden tool syntax."
                        ),
                    }
                )
                continue
            return cleaned, tool_results_log

        assistant_tool_calls = []
        for tool_call in tool_calls:
            assistant_tool_calls.append(
                {
                    "id": tool_call["id"],
                    "type": "function",
                    "function": {"name": tool_call["name"], "arguments": json.dumps(tool_call["args"])},
                }
            )

        messages.append({"role": "assistant", "content": content if content else None, "tool_calls": assistant_tool_calls})

        for tool_call in tool_calls:
            result = _execute_tool(tool_call["name"], tool_call["args"])
            tool_results_log.append({"tool": tool_call["name"], "args": tool_call["args"], "result": result})
            messages.append({"role": "tool", "tool_call_id": tool_call["id"], "content": json.dumps(result)})

    if tool_results_log:
        fallback_messages = [
            {"role": "system", "content": _system_prompt(TOOLS)},
            {
                "role": "user",
                "content": (
                    f"User question: {message}\n\n"
                    "Tool results are below. Write a polished, concise plain-English answer. "
                    "Do not include tool syntax or hidden calls.\n"
                    f"{json.dumps({'tool_results': tool_results_log}, default=str)}"
                ),
            },
        ]
        payload = {
            "model": model,
            "messages": fallback_messages,
            "temperature": 0.1,
            "max_tokens": 500,
        }
        response = httpx.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=30.0)
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0].get("message", {}).get("content", "") if data.get("choices") else ""
        return _clean_response(content), tool_results_log

    return _clean_response("I couldn't resolve a final answer from the available tools."), tool_results_log


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/coach", response_model=CoachResponse)
def coach(request: CoachRequest) -> CoachResponse:
    reply, tool_results = run_agentic_query(request.message, request.history)
    return CoachResponse(reply=reply, tool_results=tool_results)
