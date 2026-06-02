"""Grounded coaching Q&A for flagged monitoring days."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pandas as pd

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4.1-mini"


def should_generate_qa(row: pd.Series) -> bool:
    tier = str(row.get("operational_alert_tier", "clear"))
    return tier in {"watch", "investigate_state", "adjust_training"}


def build_context_pack(
    row: pd.Series,
    rationale_excerpt: str,
    period_summary: str | None = None,
) -> dict[str, Any]:
    return {
        "date": str(pd.Timestamp(row["date"]).date()),
        "operational_alert_tier": row.get("operational_alert_tier"),
        "operational_alert_label": row.get("operational_alert_label"),
        "monitoring_signal_agreement": row.get("monitoring_signal_agreement"),
        "literature_score": row.get("literature_bone_stress_score"),
        "personalized_score": row.get("personalized_bone_stress_score"),
        "frontier_score": row.get("accumulated_frontier_state"),
        "combined_score": row.get("bone_stress_risk_score"),
        "dominant_reason": row.get("bone_stress_risk_reason"),
        "run7_km": round(float(row.get("running_7d_sum_m") or 0) / 1000.0, 1),
        "accumulated_state": row.get("accumulated_bone_stress_state"),
        "counterfactual_hint": row.get("counterfactual_hint"),
        "whatif_best_scenario": row.get("whatif_best_scenario_summary"),
        "reference_archetype": row.get("reference_archetype_label"),
        "embedding_neighbors": row.get("embedding_neighbor_summary"),
        "frontier_attribution": row.get("frontier_attribution_summary"),
        "frontier_drivers": row.get("frontier_attribution_drivers"),
        "period_context": period_summary,
        "scientific_rationale_excerpt": rationale_excerpt[:2500],
    }


def build_prompt(context: dict[str, Any]) -> list[dict[str, str]]:
    system = (
        "You are a sports-science coach assistant. Answer using ONLY the structured context provided. "
        "Do not invent scores, dates, or injuries. If uncertain, say what data is missing. "
        "Answer three questions in markdown with short sections: "
        "1) Was this day risky or just different? "
        "2) Is this mainly a load signal or recovery signal? "
        "3) What should change this week?"
    )
    user = (
        "Structured athlete monitoring context (JSON):\n"
        f"{json.dumps(context, indent=2, default=str)}\n\n"
        "Ground answers in the context fields and the scientific rationale excerpt."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def call_openai(
    messages: list[dict[str, str]],
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
    timeout: int = 60,
) -> str:
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    payload = json.dumps(
        {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 900,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        OPENAI_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API request failed ({exc.code}): {detail}") from exc

    choices = body.get("choices") or []
    if not choices:
        raise RuntimeError("API returned no choices.")
    return str(choices[0]["message"]["content"]).strip()


def load_rationale_excerpt(path: Path, max_chars: int = 2500) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")[:max_chars]


def active_period_summary(periods: pd.DataFrame, target_date: pd.Timestamp) -> str | None:
    if periods.empty:
        return None
    periods = periods.copy()
    periods["start_date"] = pd.to_datetime(periods["start_date"])
    periods["end_date"] = pd.to_datetime(periods["end_date"])
    grace = pd.Timedelta(days=7)
    for _, period in periods.sort_values("peak_accumulated_bone_stress_state", ascending=False).iterrows():
        if period["start_date"] <= target_date <= period["end_date"] + grace:
            return str(period.get("period_summary") or period.get("dominant_bone_stress_reason"))
    return None


def generate_coaching_entries(
    scores: pd.DataFrame,
    periods: pd.DataFrame,
    rationale_path: Path,
    model: str = DEFAULT_MODEL,
    recent_days: int = 14,
    max_entries: int = 5,
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    scores = scores.sort_values("date")
    rationale = load_rationale_excerpt(rationale_path)
    cutoff = scores["date"].max() - pd.Timedelta(days=recent_days)
    candidates = scores[(scores["date"] >= cutoff) & scores.apply(should_generate_qa, axis=1)]
    candidates = candidates.sort_values("date", ascending=False).head(max_entries)
    entries: list[dict[str, Any]] = []

    for _, row in candidates.iterrows():
        context = build_context_pack(
            row,
            rationale,
            period_summary=active_period_summary(periods, pd.Timestamp(row["date"])),
        )
        messages = build_prompt(context)
        try:
            answer = call_openai(messages, model=model, api_key=api_key)
            status = "ok"
            error = None
        except RuntimeError as exc:
            answer = None
            status = "error"
            error = str(exc)

        entries.append(
            {
                "date": context["date"],
                "tier": context["operational_alert_tier"],
                "agreement": context["monitoring_signal_agreement"],
                "context": context,
                "answer_markdown": answer,
                "status": status,
                "error": error,
            }
        )
        if status == "error" and "OPENAI_API_KEY" in (error or ""):
            break
    return entries
