"""Retrospective evaluation of bone-stress monitoring against labeled outcome events."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def load_outcome_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_scores(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, parse_dates=["date"])
    return frame.sort_values("date").reset_index(drop=True)


def load_periods(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, parse_dates=["start_date", "end_date"])


def first_threshold_crossing(
    frame: pd.DataFrame,
    end_date: pd.Timestamp,
    lookback_days: int,
    column: str,
    threshold: float,
) -> dict[str, object] | None:
    window = frame[(frame["date"] >= end_date - pd.Timedelta(days=lookback_days)) & (frame["date"] < end_date)]
    elevated = window[window[column] >= threshold]
    if elevated.empty:
        return None
    first = elevated.iloc[0]
    return {
        "date": first["date"].date().isoformat(),
        "value": float(first[column]),
        "lead_days": int((end_date - first["date"]).days),
    }


def window_peak(frame: pd.DataFrame, end_date: pd.Timestamp, lookback_days: int) -> dict[str, object]:
    window = frame[(frame["date"] >= end_date - pd.Timedelta(days=lookback_days)) & (frame["date"] < end_date)]
    if window.empty:
        return {}
    peak_idx = window["accumulated_bone_stress_state"].idxmax()
    peak_row = window.loc[peak_idx]
    run7_km = float(peak_row["running_7d_sum_m"]) / 1000.0 if pd.notna(peak_row.get("running_7d_sum_m")) else None
    return {
        "peak_accumulated_state_date": peak_row["date"].date().isoformat(),
        "peak_accumulated_bone_stress_state": float(peak_row["accumulated_bone_stress_state"]),
        "peak_bone_stress_risk_score": float(peak_row["bone_stress_risk_score"]),
        "peak_running_7d_km": run7_km,
        "high_bone_stress_days_in_window": int((window["bone_stress_risk_level"] == "high").sum()),
    }


def sanitize_for_json(value: object) -> object:
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, dict):
        return {key: sanitize_for_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_for_json(item) for item in value]
    if isinstance(value, (float, int, str, bool)) or value is None:
        return value
    if pd.isna(value):
        return None
    return str(value)


def overlapping_periods(
    periods: pd.DataFrame,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> list[dict[str, object]]:
    if periods.empty:
        return []
    overlaps = periods[
        (periods["start_date"] <= end_date) & (periods["end_date"] >= start_date)
    ].sort_values("peak_accumulated_bone_stress_state", ascending=False)
    return [sanitize_for_json(record) for record in overlaps.to_dict(orient="records")]


def evaluate_event(
    event: dict,
    scores: pd.DataFrame,
    periods: pd.DataFrame,
    lookback_days: int,
    thresholds: list[float],
) -> dict[str, object]:
    onset = pd.Timestamp(event["onset_date"])
    symptom_start = pd.Timestamp(event.get("symptom_window_start", event["onset_date"]))
    peak = window_peak(scores, onset, lookback_days)
    crossings = {
        str(threshold): first_threshold_crossing(
            scores,
            onset,
            lookback_days,
            "accumulated_bone_stress_state",
            threshold,
        )
        for threshold in thresholds
    }
    matched_periods = overlapping_periods(periods, symptom_start, onset)
    return {
        "id": event["id"],
        "label": event["label"],
        "onset_date": onset.date().isoformat(),
        "symptom_window_start": symptom_start.date().isoformat(),
        "lookback_days": lookback_days,
        "notes": event.get("notes"),
        "window_peak": peak,
        "threshold_crossings": crossings,
        "overlapping_bone_stress_periods": matched_periods[:5],
        "detected_warning_period": bool(matched_periods),
    }


def build_markdown(report: dict) -> str:
    lines = [
        "# Bone-Stress Outcome Evaluation",
        "",
        report.get("interpretation", ""),
        "",
    ]
    for result in report["events"]:
        lines.extend(
            [
                f"## {result['label']}",
                "",
                f"- **Onset date (configured):** {result['onset_date']}",
                f"- **Symptom window start:** {result['symptom_window_start']}",
                f"- **Lookback:** {result['lookback_days']} days before onset",
                "",
            ]
        )
        peak = result.get("window_peak") or {}
        if peak:
            lines.extend(
                [
                    "### Peak load in lookback window",
                    "",
                    f"- Peak accumulated bone-stress state: **{peak.get('peak_accumulated_bone_stress_state', 'n/a')}** "
                    f"on {peak.get('peak_accumulated_state_date', 'n/a')}",
                    f"- Peak daily bone-stress score: {peak.get('peak_bone_stress_risk_score', 'n/a')}",
                    f"- Peak 7-day running total: {peak.get('peak_running_7d_km', 'n/a')} km",
                    f"- High bone-stress days in window: {peak.get('high_bone_stress_days_in_window', 'n/a')}",
                    "",
                ]
            )
        lines.append("### Threshold lead time")
        lines.append("")
        for threshold, crossing in (result.get("threshold_crossings") or {}).items():
            if crossing:
                lines.append(
                    f"- State ≥ {threshold}: first crossed on **{crossing['date']}** "
                    f"({crossing['lead_days']} days before onset, value {crossing['value']:.1f})"
                )
            else:
                lines.append(f"- State ≥ {threshold}: not crossed in lookback window")
        lines.append("")
        if result.get("detected_warning_period"):
            lines.append("### Overlapping bone-stress periods")
            lines.append("")
            for period in result["overlapping_bone_stress_periods"]:
                lines.append(
                    f"- {period['start_date']} → {period['end_date']} "
                    f"(peak state {period['peak_accumulated_bone_stress_state']:.1f}, "
                    f"peak 7d run {period.get('peak_running_7d_km', 'n/a')} km)"
                )
        else:
            lines.append("No detected bone-stress period overlapped the configured symptom window.")
        if result.get("notes"):
            lines.extend(["", f"_{result['notes']}_"])
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def build_interpretation(results: list[dict]) -> str:
    if not results:
        return "No outcome events configured."
    parts = []
    for result in results:
        peak = result.get("window_peak") or {}
        crossing_65 = (result.get("threshold_crossings") or {}).get("65")
        if crossing_65:
            parts.append(
                f"Before {result['label']}, accumulated bone-stress state crossed the high threshold "
                f"({crossing_65['lead_days']} days before configured onset)."
            )
        elif peak.get("peak_accumulated_bone_stress_state"):
            parts.append(
                f"Before {result['label']}, accumulated bone-stress state peaked at "
                f"{peak['peak_accumulated_bone_stress_state']:.0f} within the lookback window."
            )
        if result.get("detected_warning_period"):
            parts.append("A detected bone-stress period overlapped the pre-onset symptom window.")
    parts.append(
        "Scoring does not use labeled events — this check asks whether the same rules would have surfaced load "
        "beforehand. That supports validation, not prediction or diagnosis."
    )
    return " ".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate bone-stress monitoring against outcome events.")
    parser.add_argument("--outcomes", type=Path, default=Path("config/outcome_events.json"))
    parser.add_argument("--scores", type=Path, default=Path("outputs/analysis/athlete_bone_stress_scores.csv"))
    parser.add_argument("--periods", type=Path, default=Path("outputs/analysis/athlete_bone_stress_periods.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/analysis"))
    args = parser.parse_args()

    config = load_outcome_config(args.outcomes)
    scores = load_scores(args.scores)
    periods = load_periods(args.periods)
    eval_cfg = config.get("evaluation", {})
    lookback_days = int(eval_cfg.get("lookback_days", 56))
    thresholds = [float(value) for value in eval_cfg.get("accumulated_thresholds", [45, 65])]

    event_results = [
        evaluate_event(event, scores, periods, lookback_days, thresholds)
        for event in config.get("events", [])
    ]
    report = {
        "lookback_days": lookback_days,
        "thresholds": thresholds,
        "events": event_results,
        "interpretation": build_interpretation(event_results),
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "bone_stress_outcome_evaluation.json"
    md_path = args.output_dir / "bone_stress_outcome_evaluation.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown(report), encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    print(report["interpretation"])


if __name__ == "__main__":
    main()
