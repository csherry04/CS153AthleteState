"""Evaluate literature, personalized, and frontier signals before labeled events."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def signal_window(scores: pd.DataFrame, end: pd.Timestamp, lookback_days: int) -> pd.DataFrame:
    return scores[(scores["date"] >= end - pd.Timedelta(days=lookback_days)) & (scores["date"] < end)]


def first_signal_day(
    window: pd.DataFrame,
    column: str,
    value,
    end: pd.Timestamp,
) -> dict[str, object] | None:
    hits = window[window[column] == value]
    if hits.empty:
        return None
    first = hits.iloc[0]
    return {
        "date": first["date"].date().isoformat(),
        "lead_days": int((end - first["date"]).days),
    }


def first_threshold_day(
    window: pd.DataFrame,
    column: str,
    threshold: float,
    end: pd.Timestamp,
) -> dict[str, object] | None:
    hits = window[pd.to_numeric(window[column], errors="coerce") >= threshold]
    if hits.empty:
        return None
    first = hits.iloc[0]
    return {
        "date": first["date"].date().isoformat(),
        "value": float(first[column]),
        "lead_days": int((end - first["date"]).days),
    }


def evaluate_target(
    target: dict,
    scores: pd.DataFrame,
    lookback_days: int,
) -> dict[str, object]:
    end = pd.Timestamp(target.get("evaluation_end") or target.get("onset_date") or target["end_date"])
    start = pd.Timestamp(target.get("symptom_window_start") or target.get("start_date") or end - pd.Timedelta(days=lookback_days))
    window = scores[(scores["date"] >= end - pd.Timedelta(days=lookback_days)) & (scores["date"] < end)]
    pre_symptom = scores[(scores["date"] >= start) & (scores["date"] < end)]

    return {
        "id": target["id"],
        "label": target.get("label", target["id"]),
        "evaluation_end": end.date().isoformat(),
        "symptom_window_start": start.date().isoformat(),
        "lookback_days": lookback_days,
        "days_in_window": int(len(window)),
        "counts": {
            "literature_high": int((window["literature_bone_stress_level"] == "high").sum()) if "literature_bone_stress_level" in window else 0,
            "personalized_high": int((window["personalized_bone_stress_level"] == "high").sum()) if "personalized_bone_stress_level" in window else 0,
            "frontier_high": int((window["frontier_strain_level"] == "high").sum()) if "frontier_strain_level" in window else 0,
            "all_agree": int((window["monitoring_signal_agreement"] == "all_agree").sum()) if "monitoring_signal_agreement" in window else 0,
            "mixed_signals": int((window["monitoring_signal_agreement"] == "mixed_signals").sum()) if "monitoring_signal_agreement" in window else 0,
            "frontier_high_literature_not": int(
                ((window["frontier_strain_level"] == "high") & (window["literature_bone_stress_level"] != "high")).sum()
            )
            if "frontier_strain_level" in window
            else 0,
        },
        "first_signals": {
            "literature_high": first_signal_day(window, "literature_bone_stress_level", "high", end),
            "personalized_high": first_signal_day(window, "personalized_bone_stress_level", "high", end),
            "frontier_high": first_signal_day(window, "frontier_strain_level", "high", end),
            "all_agree": first_signal_day(window, "monitoring_signal_agreement", "all_agree", end),
            "mixed_signals": first_signal_day(window, "monitoring_signal_agreement", "mixed_signals", end),
            "frontier_score_70": first_threshold_day(window, "frontier_strain_score", 70.0, end),
            "integrated_score_70": first_threshold_day(window, "integrated_bone_stress_score", 70.0, end),
        },
        "peak_in_window": {
            "frontier_strain_score": float(window["frontier_strain_score"].max()) if window["frontier_strain_score"].notna().any() else None,
            "literature_bone_stress_score": float(window["literature_bone_stress_score"].max()),
            "personalized_bone_stress_score": float(window["personalized_bone_stress_score"].max()),
            "bone_stress_risk_score": float(window["bone_stress_risk_score"].max()),
        },
        "pre_symptom_high_days": int((pre_symptom["bone_stress_risk_level"] == "high").sum()) if not pre_symptom.empty else 0,
        "notes": target.get("notes"),
    }


def build_markdown(report: dict) -> str:
    lines = [
        "# Frontier Outcome Evaluation",
        "",
        report.get("interpretation", ""),
        "",
    ]
    for result in report["targets"]:
        lines.extend(
            [
                f"## {result['label']}",
                "",
                f"- Evaluation end: **{result['evaluation_end']}**",
                f"- Symptom / reference window start: **{result['symptom_window_start']}**",
                f"- Lookback: {result['lookback_days']} days",
                "",
                "### Signal counts in lookback",
                "",
            ]
        )
        for key, value in result["counts"].items():
            lines.append(f"- {key.replace('_', ' ')}: **{value}**")
        lines.extend(["", "### First alert lead time", ""])
        for key, value in result["first_signals"].items():
            if value:
                extra = f", value {value['value']:.1f}" if "value" in value else ""
                lines.append(f"- {key.replace('_', ' ')}: **{value['date']}** ({value['lead_days']} days before{extra})")
            else:
                lines.append(f"- {key.replace('_', ' ')}: not observed in lookback")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def build_interpretation(results: list[dict]) -> str:
    if not results:
        return "No evaluation targets configured."
    parts = []
    for result in results:
        frontier_first = result["first_signals"].get("frontier_high")
        lit_first = result["first_signals"].get("literature_high")
        if frontier_first and lit_first:
            parts.append(
                f"Before {result['label']}, frontier high preceded literature high by "
                f"{lit_first['lead_days'] - frontier_first['lead_days']} days "
                f"(frontier {frontier_first['lead_days']}d, literature {lit_first['lead_days']}d lead)."
            )
        elif frontier_first:
            parts.append(f"Before {result['label']}, frontier flagged high with {frontier_first['lead_days']} days lead.")
        elif lit_first:
            parts.append(f"Before {result['label']}, literature flagged high with {lit_first['lead_days']} days lead.")
        all_agree = result["first_signals"].get("all_agree")
        if all_agree:
            parts.append(f"All three tracks agreed on {all_agree['date']} ({all_agree['lead_days']} days before).")
    parts.append("Events and reference periods are for validation only — scoring never uses these dates.")
    return " ".join(parts)


def evaluation_targets(config: dict) -> list[dict]:
    targets = []
    for event in config.get("events", []):
        targets.append(
            {
                **event,
                "evaluation_end": event.get("onset_date"),
            }
        )
    for ref in config.get("reference_periods", []):
        targets.append(
            {
                **ref,
                "evaluation_end": ref.get("evaluation_end") or ref.get("end_date"),
            }
        )
    return targets


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate frontier and rule tracks before labeled/reference events.")
    parser.add_argument("--outcomes", type=Path, default=Path("config/outcome_events.json"))
    parser.add_argument("--scores", type=Path, default=Path("outputs/analysis/athlete_bone_stress_scores.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/analysis"))
    args = parser.parse_args()

    config = load_config(args.outcomes)
    scores = pd.read_csv(args.scores, parse_dates=["date"]).sort_values("date")
    lookback_days = int(config.get("evaluation", {}).get("lookback_days", 56))
    results = [evaluate_target(target, scores, lookback_days) for target in evaluation_targets(config)]
    report = {
        "lookback_days": lookback_days,
        "targets": results,
        "interpretation": build_interpretation(results),
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "frontier_outcome_evaluation.json"
    md_path = args.output_dir / "frontier_outcome_evaluation.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown(report), encoding="utf-8")
    print(f"Wrote {json_path}")
    print(report["interpretation"])


if __name__ == "__main__":
    main()
