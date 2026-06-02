"""Generate athlete-facing explanations from embedding anomaly reports."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / "outputs" / ".matplotlib"))

import numpy as np
import pandas as pd


CONTEXT_COLUMNS = [
    "readiness",
    "load",
    "hrv",
    "resting_hr",
    "activity_count",
    "activity_duration_seconds",
    "activity_distance_m",
    "activity_calories",
    "activity_avg_hr",
    "activity_max_hr",
    "activity_steps",
]

CANONICAL_COLUMN_CANDIDATES = {
    "readiness": ["readiness", "readiness_score"],
    "load": ["load", "load_dailyTrainingLoadAcute", "activity_training_load", "readiness_acuteLoad"],
    "hrv": ["hrv", "readiness_hrvWeeklyAverage"],
    "resting_hr": ["resting_hr", "wellness_restingHeartRate", "wellness_currentDayRestingHeartRate"],
}

SCIENTIFIC_REFERENCES = {
    "acwr": "Maupin et al. (2020) [1]; Griffin et al. (2020) [2] — acute vs chronic workload context",
    "hrv": "Vesterinen et al. (2016) [3]; Granero-Gallegos et al. (2020) [4] — HRV/readiness-guided recovery",
    "monotony": "Foster (1998) [5] — training monotony, strain, and insufficient restoration",
    "running_load": "Schmitz et al. (2022) [6]; Matijevich et al. (2020) [7] — running tissue load is multifactorial",
    "preparedness": "Preparedness mismatch hypothesis (SCIENTIFIC_RATIONALE.md §5)",
    "sport_specific": "Sport-specific load weighting (SCIENTIFIC_RATIONALE.md §4, §7)",
}


def numeric_value(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def score_band(value: float | None, high: float = 60.0, moderate: float = 40.0) -> str | None:
    if value is None:
        return None
    if value >= high:
        return "high"
    if value >= moderate:
        return "moderate"
    return "low"


def sport_load_story(row: pd.Series) -> str:
    running_distance = numeric_value(row.get("running_distance"))
    cycling_distance = numeric_value(row.get("cycling_distance"))
    previous_running = numeric_value(row.get("previous_day_running_distance"))
    previous_cycling = numeric_value(row.get("previous_day_cycling_distance"))
    parts = []
    if running_distance and running_distance > 0:
        parts.append(f"running {fmt(running_distance, 0)} m today")
    if cycling_distance and cycling_distance > 0:
        parts.append(f"cycling {fmt(cycling_distance, 0)} m today")
    if previous_running and previous_running > 0:
        parts.append(f"after {fmt(previous_running, 0)} m running yesterday")
    if previous_cycling and previous_cycling > 0:
        parts.append(f"after {fmt(previous_cycling, 0)} m cycling yesterday")
    if not parts:
        prior_distance = numeric_value(row.get("previous_day_distance"))
        if prior_distance and prior_distance > 0:
            parts.append(f"after a large prior-day workload ({fmt(prior_distance, 0)} m total)")
    return "; ".join(parts) if parts else "without a clearly dominant sport-specific load signal"


def recovery_story(row: pd.Series) -> str:
    readiness = numeric_value(row.get("readiness"))
    hrv = numeric_value(row.get("hrv"))
    resting_hr = numeric_value(row.get("resting_hr"))
    parts = []
    if readiness is not None and readiness < 35:
        parts.append(f"readiness was very suppressed ({fmt(readiness)})")
    elif readiness is not None and readiness < 50:
        parts.append(f"readiness was below typical ({fmt(readiness)})")
    if hrv is not None:
        parts.append(f"HRV context {fmt(hrv)}")
    if resting_hr is not None:
        parts.append(f"resting HR {fmt(resting_hr)}")
    return ", ".join(parts) if parts else "recovery markers were mixed or incomplete"


def mechanism_tags(row: pd.Series) -> list[str]:
    tags: list[str] = []
    recovery = numeric_value(row.get("recovery_strain_score")) or 0.0
    metabolic = numeric_value(row.get("metabolic_fatigue_score")) or 0.0
    tissue = numeric_value(row.get("tissue_load_score")) or 0.0
    insufficient = numeric_value(row.get("insufficient_rest_score")) or 0.0
    mismatch = numeric_value(row.get("preparedness_mismatch_score")) or 0.0
    if recovery >= 55:
        tags.append("autonomic recovery strain")
    if metabolic >= 55:
        tags.append("metabolic fatigue")
    if tissue >= 55:
        tags.append("tissue-load stress")
    if insufficient >= 55:
        tags.append("insufficient rest / monotony")
    if mismatch >= 55:
        tags.append("preparedness mismatch")
    reason = str(row.get("risk_reason", ""))
    if reason == "running while under-recovered":
        tags.append("running under-recovered")
    if not tags:
        tags.append("mixed monitoring signal")
    return tags


def science_references_for_tags(tags: list[str], reason: str = "") -> str:
    refs: list[str] = []
    if any(tag in tags for tag in ["autonomic recovery strain", "preparedness mismatch"]) or reason in {
        "post-load recovery response",
        "poor recovery markers",
        "running while under-recovered",
    }:
        refs.append(SCIENTIFIC_REFERENCES["hrv"])
    if any(tag in tags for tag in ["metabolic fatigue", "preparedness mismatch", "insufficient rest / monotony"]):
        refs.append(SCIENTIFIC_REFERENCES["acwr"])
    if "insufficient rest / monotony" in tags or reason == "accumulated insufficient rest":
        refs.append(SCIENTIFIC_REFERENCES["monotony"])
    if any(tag in tags for tag in ["tissue-load stress", "running under-recovered"]) or reason == "tissue-load recovery mismatch":
        refs.append(SCIENTIFIC_REFERENCES["running_load"])
        refs.append(SCIENTIFIC_REFERENCES["sport_specific"])
    if "preparedness mismatch" in tags or reason in {
        "post-load recovery response",
        "tissue-load recovery mismatch",
        "running while under-recovered",
        "accumulated insufficient rest",
    }:
        refs.append(SCIENTIFIC_REFERENCES["preparedness"])
    seen: list[str] = []
    for ref in refs:
        if ref not in seen:
            seen.append(ref)
    return " · ".join(seen)


def what_is_happening_day(row: pd.Series) -> str:
    reason = str(row.get("risk_reason", "risk signal"))
    load_story = sport_load_story(row)
    recovery = recovery_story(row)
    accumulated = numeric_value(row.get("accumulated_risk_state"))
    accumulated_clause = (
        f" Accumulated risk state was {fmt(accumulated, 1)}, meaning recent load and recovery context had not fully cleared."
        if accumulated is not None and accumulated >= 45
        else ""
    )
    if reason == "post-load recovery response":
        return (
            f"This day looks like a delayed recovery response: {recovery}, {load_story}. "
            f"The system is interpreting this as workload absorbed recently outpacing current recovery capacity.{accumulated_clause}"
        )
    if reason == "accumulated insufficient rest":
        return (
            f"This day sits inside a broader under-recovery pattern: {recovery}, with repeated recent load and limited restoration. "
            f"{load_story.capitalize()}.{accumulated_clause}"
        )
    if reason == "tissue-load recovery mismatch":
        return (
            f"This day shows a tissue-load mismatch: impact-weighted or running-heavy stress was high while {recovery}. "
            f"Weight-bearing load likely exceeded what recovery markers suggested you were prepared to absorb. {load_story.capitalize()}.{accumulated_clause}"
        )
    if reason == "running while under-recovered":
        return (
            f"Running load occurred while recovery markers were already suppressed ({recovery}). "
            f"This is more concerning than equivalent cycling because running adds repetitive tissue stress on top of autonomic fatigue. {load_story.capitalize()}.{accumulated_clause}"
        )
    if reason == "poor recovery markers":
        return (
            f"Recovery markers alone drove the alert: {recovery}. Workload context was secondary on this day.{accumulated_clause}"
        )
    return (
        f"Risk was elevated because {', '.join(mechanism_tags(row))} combined on this day. {recovery.capitalize()}; {load_story}.{accumulated_clause}"
    )


def science_rationale_day(row: pd.Series) -> str:
    tags = mechanism_tags(row)
    reason = str(row.get("risk_reason", ""))
    bullets = []
    if "autonomic recovery strain" in tags:
        bullets.append(
            "Recovery strain combines readiness, HRV, resting HR, sleep, and body battery versus your 28-day baseline. "
            "HRV and readiness are most meaningful as individual trends, not isolated values [3,4]."
        )
    if "metabolic fatigue" in tags:
        bullets.append(
            "Metabolic fatigue reflects recent training load and fatigue-weighted sport duration. "
            "External workload only becomes risky when internal recovery appears insufficient [1,2]."
        )
    if "tissue-load stress" in tags or "running under-recovered" in tags:
        bullets.append(
            "Running and hiking receive higher tissue-load weight than cycling because they are weight-bearing. "
            "This does not predict injury by itself, but hard running while under-recovered is a preparedness mismatch [6,7]."
        )
    if "insufficient rest / monotony" in tags or reason == "accumulated insufficient rest":
        bullets.append(
            "Repeated high-load days with too little easy recovery resemble elevated training monotony/strain patterns described by Foster [5]."
        )
    if "preparedness mismatch" in tags:
        bullets.append(
            "The central project hypothesis is preparedness mismatch: demand exceeded what recovery markers suggested you could absorb [SCIENTIFIC_RATIONALE.md §5]."
        )
    if not bullets:
        bullets.append(
            "This alert is based on a multivariate monitoring model, not a single Garmin score. It should support training decisions, not replace them."
        )
    return " ".join(bullets)


def period_mechanism_tags(row: pd.Series) -> list[str]:
    tags: list[str] = []
    mean_recovery = numeric_value(row.get("mean_recovery_strain")) or 0.0
    mean_metabolic = numeric_value(row.get("mean_metabolic_fatigue")) or 0.0
    mean_tissue = numeric_value(row.get("mean_tissue_load")) or 0.0
    high_risk_days = numeric_value(row.get("high_risk_days")) or 0.0
    if mean_metabolic >= 80:
        tags.append("sustained metabolic load")
    if mean_tissue >= 55:
        tags.append("sustained tissue-load exposure")
    if mean_recovery >= 45:
        tags.append("suppressed recovery markers")
    if high_risk_days == 0 and numeric_value(row.get("peak_accumulated_risk_state")) or 0 >= 60:
        tags.append("chronic load without daily spikes")
    reason = str(row.get("dominant_risk_reason", ""))
    if reason == "accumulated insufficient rest":
        tags.append("insufficient rest / monotony")
    return tags or ["sustained accumulated risk"]


def what_is_happening_period(row: pd.Series) -> str:
    start = row.get("start_date")
    end = row.get("end_date")
    days = row.get("calendar_days")
    peak = numeric_value(row.get("peak_accumulated_risk_state"))
    mean_state = numeric_value(row.get("mean_accumulated_risk_state"))
    high_days = numeric_value(row.get("high_risk_days")) or 0
    min_readiness = numeric_value(row.get("min_readiness"))
    tags = period_mechanism_tags(row)
    readiness_clause = f" Readiness dropped as low as {fmt(min_readiness)} during the block." if min_readiness is not None else ""
    if "chronic load without daily spikes" in tags:
        return (
            f"From {start} to {end} ({days} days), accumulated risk stayed elevated (peak {fmt(peak, 1)}, mean {fmt(mean_state, 1)}) "
            f"even though only {int(high_days)} day(s) crossed the high daily-risk threshold. "
            f"This pattern fits a chronic load block: metabolic fatigue accumulated faster than recovery cleared it.{readiness_clause}"
        )
    if "insufficient rest / monotony" in tags:
        return (
            f"From {start} to {end} ({days} days), the athlete likely did not get enough restoration relative to repeated workload. "
            f"Accumulated state peaked at {fmt(peak, 1)} with {int(high_days)} high-risk day(s).{readiness_clause} "
            f"This is closer to a training-strain block than a single bad day."
        )
    if "sustained tissue-load exposure" in tags and "suppressed recovery markers" in tags:
        return (
            f"From {start} to {end} ({days} days), tissue-load and recovery markers diverged: impact-weighted stress stayed high while recovery remained suppressed. "
            f"Peak accumulated state {fmt(peak, 1)}.{readiness_clause}"
        )
    return (
        f"From {start} to {end} ({days} days), accumulated risk state remained elevated (peak {fmt(peak, 1)}, mean {fmt(mean_state, 1)}). "
        f"Dominant mechanisms: {', '.join(tags)}.{readiness_clause}"
    )


def science_rationale_period(row: pd.Series) -> str:
    tags = period_mechanism_tags(row)
    bullets = []
    if "sustained metabolic load" in tags or "chronic load without daily spikes" in tags:
        bullets.append(
            "Sustained metabolic load resembles an acute:chronic workload imbalance: recent stress stayed high relative to restoration [1,2]. "
            "Cycling and long endurance sessions can drive this even when daily readiness looks acceptable."
        )
    if "insufficient rest / monotony" in tags:
        bullets.append(
            "Foster's monotony/strain framework is relevant here: repeated load without enough low-load variation can suppress adaptation and recovery [5]."
        )
    if "suppressed recovery markers" in tags:
        bullets.append(
            "HRV/readiness-guided training literature supports treating multi-day suppression as a signal to reduce intensity rather than chase a plan [3,4]."
        )
    if "sustained tissue-load exposure" in tags:
        bullets.append(
            "Running and hiking contribute more tissue-load weight than cycling in this model. The goal is preparedness monitoring, not injury prediction [6,7]."
        )
    bullets.append(
        "Period detection uses decaying accumulated risk state, so the block reflects how load and recovery interacted over time rather than isolated daily flags."
    )
    return " ".join(bullets)


def first_available(frame: pd.DataFrame, candidates: list[str]) -> str | None:
    return next((column for column in candidates if column in frame.columns), None)


def fmt(value: object, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "unknown"
    if isinstance(value, (int, np.integer)):
        return f"{value:,}"
    if isinstance(value, (float, np.floating)):
        return f"{value:,.{digits}f}"
    return str(value)


def pct_delta(value: float | None, baseline: float | None) -> float | None:
    if value is None or baseline is None or pd.isna(value) or pd.isna(baseline) or baseline == 0:
        return None
    return float((value - baseline) / abs(baseline) * 100)


def direction_phrase(delta: float | None, higher_word: str = "higher", lower_word: str = "lower") -> str | None:
    if delta is None or pd.isna(delta):
        return None
    if abs(delta) < 10:
        return None
    return f"{abs(delta):.0f}% {higher_word if delta > 0 else lower_word} than recent baseline"


def parse_neighbors(value: object) -> list[dict[str, object]]:
    if pd.isna(value):
        return []
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def load_context_frame(embeddings_path: Path, daily_features_path: Path) -> pd.DataFrame:
    embeddings = pd.read_csv(embeddings_path, parse_dates=["date"])
    daily = pd.read_csv(daily_features_path, parse_dates=["date"])
    frame = embeddings.merge(daily, on="date", how="left").sort_values("date").reset_index(drop=True)
    for canonical, candidates in CANONICAL_COLUMN_CANDIDATES.items():
        source = first_available(frame, candidates)
        if source and canonical not in frame.columns:
            frame[canonical] = frame[source]
    return frame


def rolling_baseline(frame: pd.DataFrame, date: pd.Timestamp, window_days: int) -> dict[str, float | None]:
    start = date - pd.Timedelta(days=window_days)
    history = frame[(frame["date"] < date) & (frame["date"] >= start)]
    baseline = {}
    for column in CONTEXT_COLUMNS:
        if column in history.columns:
            baseline[column] = pd.to_numeric(history[column], errors="coerce").median()
        else:
            baseline[column] = None
    return baseline


def previous_day_context(frame: pd.DataFrame, date: pd.Timestamp) -> pd.Series | None:
    previous_date = date - pd.Timedelta(days=1)
    matches = frame[frame["date"].dt.date == previous_date.date()]
    if matches.empty:
        return None
    return matches.iloc[-1]


def classify_state(row: pd.Series, baseline: dict[str, float | None], previous_day: pd.Series | None = None) -> list[str]:
    tags = []
    readiness = row.get("readiness")
    load = row.get("load")
    resting_hr = row.get("resting_hr")
    duration = row.get("activity_duration_seconds")
    distance = row.get("activity_distance_m")
    avg_hr = row.get("activity_avg_hr")

    if pd.notna(readiness) and readiness < 30:
        tags.append("very low readiness")
    elif pd.notna(readiness) and readiness < 50:
        tags.append("suppressed readiness")

    load_delta = pct_delta(load, baseline.get("load"))
    if load_delta is not None and load_delta > 25:
        tags.append("elevated training load")
    elif load_delta is not None and load_delta < -25:
        tags.append("low training load")

    rhr_delta = pct_delta(resting_hr, baseline.get("resting_hr"))
    if rhr_delta is not None and rhr_delta > 5:
        tags.append("elevated resting HR")

    duration_delta = pct_delta(duration, baseline.get("activity_duration_seconds"))
    distance_delta = pct_delta(distance, baseline.get("activity_distance_m"))
    if duration_delta is not None and duration_delta > 40:
        tags.append("long activity day")
    if distance_delta is not None and distance_delta > 40:
        tags.append("high-distance day")

    avg_hr_delta = pct_delta(avg_hr, baseline.get("activity_avg_hr"))
    if avg_hr_delta is not None and avg_hr_delta > 8:
        tags.append("higher activity HR")

    if previous_day is not None:
        previous_load_delta = pct_delta(previous_day.get("load"), baseline.get("load"))
        previous_duration_delta = pct_delta(previous_day.get("activity_duration_seconds"), baseline.get("activity_duration_seconds"))
        previous_distance_delta = pct_delta(previous_day.get("activity_distance_m"), baseline.get("activity_distance_m"))
        if (
            (previous_load_delta is not None and previous_load_delta > 25)
            or (previous_duration_delta is not None and previous_duration_delta > 40)
            or (previous_distance_delta is not None and previous_distance_delta > 40)
        ):
            tags.append("possible prior-day workload response")

    if not tags:
        tags.append("unusual latent state without one obvious driver")
    return tags


def evidence_bullets(row: pd.Series, baseline: dict[str, float | None], previous_day: pd.Series | None = None) -> list[str]:
    checks = [
        ("Readiness", "readiness", "higher", "lower"),
        ("Training load", "load", "higher", "lower"),
        ("Resting HR", "resting_hr", "higher", "lower"),
        ("Activity duration", "activity_duration_seconds", "longer", "shorter"),
        ("Activity distance", "activity_distance_m", "higher", "lower"),
        ("Average activity HR", "activity_avg_hr", "higher", "lower"),
    ]
    bullets = []
    for label, column, higher_word, lower_word in checks:
        if column not in row:
            continue
        value = row.get(column)
        base = baseline.get(column)
        delta = pct_delta(value, base)
        phrase = direction_phrase(delta, higher_word=higher_word, lower_word=lower_word)
        if phrase:
            bullets.append(f"{label}: {fmt(value)} vs recent median {fmt(base)} ({phrase}).")
    if not bullets:
        bullets.append("No single raw metric strongly deviated from the recent baseline, so the anomaly may reflect the combination of features.")
    if previous_day is not None:
        prior_bits = []
        for label, column, higher_word, lower_word in [
            ("prior-day load", "load", "higher", "lower"),
            ("prior-day duration", "activity_duration_seconds", "longer", "shorter"),
            ("prior-day distance", "activity_distance_m", "higher", "lower"),
        ]:
            value = previous_day.get(column)
            base = baseline.get(column)
            phrase = direction_phrase(pct_delta(value, base), higher_word=higher_word, lower_word=lower_word)
            if phrase:
                prior_bits.append(f"{label} was {fmt(value)} vs recent median {fmt(base)} ({phrase})")
        if prior_bits:
            bullets.append("Previous-day context: " + "; ".join(prior_bits) + ".")
    return bullets


def recommendation(tags: list[str]) -> str:
    tag_set = set(tags)
    if "very low readiness" in tag_set and ("elevated training load" in tag_set or "long activity day" in tag_set or "high-distance day" in tag_set):
        return "Treat this as a high-risk recovery signal: reduce intensity, prioritize sleep/fueling, and compare the next 24-48 hours of readiness before adding hard work."
    if "possible prior-day workload response" in tag_set and ("very low readiness" in tag_set or "suppressed readiness" in tag_set):
        return "Likely delayed recovery from prior workload: keep the next session easy and watch whether readiness rebounds after a lighter day."
    if "very low readiness" in tag_set or "suppressed readiness" in tag_set:
        return "Use this as a recovery check: keep training easy until readiness and resting markers normalize."
    if "elevated training load" in tag_set or "long activity day" in tag_set or "high-distance day" in tag_set:
        return "Likely a major workload state: monitor next-day readiness and avoid stacking another hard session unless recovery markers stay stable."
    if "elevated resting HR" in tag_set:
        return "Watch for illness, stress, dehydration, or poor sleep signals before prescribing intensity."
    return "Review this day manually against training notes; the embedding changed more than the individual summary metrics suggest."


def build_feedback(anomalies: pd.DataFrame, full_frame: pd.DataFrame, baseline_days: int) -> pd.DataFrame:
    rows = []
    full_frame = full_frame.sort_values("date").reset_index(drop=True)
    for _, row in anomalies.iterrows():
        date = pd.to_datetime(row["date"])
        baseline = rolling_baseline(full_frame, date, baseline_days)
        previous_day = previous_day_context(full_frame, date)
        tags = classify_state(row, baseline, previous_day=previous_day)
        neighbors = parse_neighbors(row.get("nearest_previous_normal_days"))
        neighbor_summary = "; ".join(
            f"{item.get('date')} (readiness {fmt(item.get('readiness'))}, load {fmt(item.get('load'))})"
            for item in neighbors[:3]
        )
        explanation = (
            f"{date.date().isoformat()} is flagged because its learned athlete-state embedding was far from the recent rolling baseline "
            f"(anomaly z-score {fmt(row.get('anomaly_zscore'), 2)}). "
            f"The main interpretation is: {', '.join(tags)}."
        )
        rows.append(
            {
                "date": date.date().isoformat(),
                "anomaly_zscore": row.get("anomaly_zscore"),
                "readiness": row.get("readiness"),
                "load": row.get("load"),
                "hrv": row.get("hrv"),
                "resting_hr": row.get("resting_hr"),
                "activity_count": row.get("activity_count"),
                "activity_duration_seconds": row.get("activity_duration_seconds"),
                "activity_distance_m": row.get("activity_distance_m"),
                "previous_day_load": None if previous_day is None else previous_day.get("load"),
                "previous_day_activity_duration_seconds": None if previous_day is None else previous_day.get("activity_duration_seconds"),
                "previous_day_activity_distance_m": None if previous_day is None else previous_day.get("activity_distance_m"),
                "tags": ", ".join(tags),
                "explanation": explanation,
                "evidence": " ".join(evidence_bullets(row, baseline, previous_day=previous_day)),
                "nearest_normal_context": neighbor_summary or "No previous normal neighbor found.",
                "suggested_action": recommendation(tags),
            }
        )
    return pd.DataFrame(rows)


def write_markdown(feedback: pd.DataFrame, output_path: Path) -> None:
    lines = [
        "# Athlete State Feedback Report",
        "",
        "This report translates embedding anomaly days into athlete-facing interpretations. It is rule-based and should be treated as decision support, not medical advice.",
        "",
    ]
    for _, row in feedback.iterrows():
        lines.extend(
            [
                f"## {row['date']}",
                "",
                f"**Summary:** {row['explanation']}",
                "",
                f"**Evidence:** {row['evidence']}",
                "",
                f"**Nearest previous normal states:** {row['nearest_normal_context']}",
                "",
                f"**Suggested action:** {row['suggested_action']}",
                "",
            ]
        )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def risk_reason_sentence(row: pd.Series) -> str:
    reason = row.get("risk_reason", "risk signal")
    if reason == "running while under-recovered":
        return "This is risky because running load occurred while recovery markers were already suppressed."
    if reason == "tissue-load recovery mismatch":
        return "This looks like a tissue-load mismatch: impact-weighted workload was high relative to the athlete's recovery state."
    if reason == "post-load recovery response":
        return "This looks like a delayed recovery response: prior workload was high and recovery markers were suppressed afterward."
    if reason == "accumulated insufficient rest":
        return "This looks like accumulated under-recovery: recent workload and recovery strain suggest there may not have been enough restoration."
    if reason == "poor recovery markers":
        return "This is risky because recovery markers are poor even without relying on activity novelty."
    if reason == "novel but not clearly risky":
        return "This day was unusual in the embedding space, but the recovery markers do not clearly make it a high-risk day."
    if reason == "low-risk rest/easy day":
        return "This appears to be a low-risk easy/rest day: activity was different from normal, but recovery strain was not elevated."
    return "This day has a low current risk score."


def build_risk_feedback(risk_rows: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in risk_rows.iterrows():
        tags = mechanism_tags(row)
        reason = str(row.get("risk_reason", ""))
        evidence = (
            f"Risk score {fmt(row.get('risk_score'), 1)} ({row.get('risk_level')}); "
            f"recovery strain {fmt(row.get('recovery_strain_score'), 1)}, "
            f"prior workload {fmt(row.get('prior_workload_score'), 1)}, "
            f"tissue load {fmt(row.get('tissue_load_score'), 1)}, "
            f"metabolic fatigue {fmt(row.get('metabolic_fatigue_score'), 1)}, "
            f"preparedness mismatch {fmt(row.get('preparedness_mismatch_score'), 1)}, "
            f"accumulated state {fmt(row.get('accumulated_risk_state'), 1)}, "
            f"insufficient-rest signal {fmt(row.get('insufficient_rest_score'), 1)}."
        )
        context = (
            f"Readiness {fmt(row.get('readiness'))}, load {fmt(row.get('load'))}, "
            f"previous-day load {fmt(row.get('previous_day_load'))}, "
            f"previous-day distance {fmt(row.get('previous_day_distance'))} m, "
            f"running distance {fmt(row.get('running_distance'))} m, "
            f"cycling distance {fmt(row.get('cycling_distance'))} m."
        )
        rows.append(
            {
                "date": row.get("date"),
                "risk_score": row.get("risk_score"),
                "risk_level": row.get("risk_level"),
                "risk_reason": row.get("risk_reason"),
                "mechanisms": ", ".join(tags),
                "summary": risk_reason_sentence(row),
                "what_is_happening": what_is_happening_day(row),
                "science_rationale": science_rationale_day(row),
                "science_references": science_references_for_tags(tags, reason=reason),
                "evidence": evidence,
                "context": context,
                "suggested_action": risk_recommendation(row),
            }
        )
    return pd.DataFrame(rows)


def risk_recommendation(row: pd.Series) -> str:
    reason = row.get("risk_reason")
    level = row.get("risk_level")
    if reason == "low-risk rest/easy day" or reason == "novel but not clearly risky":
        return "Do not treat this as a warning by itself; review context, but avoid escalating solely because activity was low or different."
    if reason == "running while under-recovered":
        return "Avoid adding intensity or volume to running until recovery markers rebound; choose low-impact aerobic work if training is needed."
    if reason == "tissue-load recovery mismatch":
        return "Reduce impact exposure and prioritize lower-impact or recovery-focused work until readiness normalizes."
    if reason == "post-load recovery response":
        return "Keep the next session easy or recovery-focused until readiness and resting markers rebound."
    if reason == "accumulated insufficient rest":
        return "Consider a lower-load block or deliberate rest day; watch whether recovery markers improve across several days."
    if reason == "poor recovery markers":
        return "Check sleep, stress, illness, hydration, and soreness before adding intensity."
    if level == "high":
        return "Treat as a high-risk training day and avoid stacking hard work."
    if level == "moderate":
        return "Proceed cautiously and prefer lower-intensity training unless recovery context improves."
    return "No major action needed from risk score alone."


def write_risk_markdown(feedback: pd.DataFrame, output_path: Path) -> None:
    lines = [
        "# Athlete Risk Feedback Report",
        "",
        "This report prioritizes recovery/training risk rather than raw embedding novelty. Explanations are grounded in the monitoring framework described in `SCIENTIFIC_RATIONALE.md`. This is decision support, not medical advice.",
        "",
    ]
    for _, row in feedback.iterrows():
        lines.extend(
            [
                f"## {row['date']}",
                "",
                f"**Summary:** {row['summary']}",
                "",
                f"**What is happening:** {row['what_is_happening']}",
                "",
                f"**Mechanisms:** {row['mechanisms']}",
                "",
                f"**Science rationale:** {row['science_rationale']}",
                "",
                f"**References:** {row['science_references']}",
                "",
                f"**Evidence:** {row['evidence']}",
                "",
                f"**Context:** {row['context']}",
                "",
                f"**Suggested action:** {row['suggested_action']}",
                "",
            ]
        )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def period_recommendation(row: pd.Series) -> str:
    reason = str(row.get("dominant_risk_reason", ""))
    if reason == "accumulated insufficient rest":
        return "Treat this as a recovery block, not isolated bad days. Reduce volume and intensity until accumulated risk state falls below moderate levels."
    if reason == "post-load recovery response":
        return "Space hard sessions further apart during this block and prioritize sleep and easy aerobic work."
    if reason == "tissue-load recovery mismatch":
        return "Shift toward lower-impact training until tissue-load and recovery markers normalize across several days."
    if reason == "running while under-recovered":
        return "Avoid stacking running intensity until readiness and accumulated risk state improve."
    if row.get("period_level") == "high":
        return "This was a sustained high-risk stretch; do not add load until accumulated risk state clearly trends down."
    return "Monitor recovery markers daily and keep training conservative until the block resolves."


def build_period_feedback(period_rows: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in period_rows.iterrows():
        tags = period_mechanism_tags(row)
        reason = str(row.get("dominant_risk_reason", ""))
        evidence = (
            f"Peak accumulated state {fmt(row.get('peak_accumulated_risk_state'), 1)}; "
            f"mean accumulated state {fmt(row.get('mean_accumulated_risk_state'), 1)}; "
            f"elevated days {fmt(row.get('elevated_days'), 0)}; "
            f"high-risk days {fmt(row.get('high_risk_days'), 0)}; "
            f"mean recovery strain {fmt(row.get('mean_recovery_strain'), 1)}; "
            f"mean metabolic fatigue {fmt(row.get('mean_metabolic_fatigue'), 1)}; "
            f"mean tissue load {fmt(row.get('mean_tissue_load'), 1)}; "
            f"min readiness {fmt(row.get('min_readiness'))}."
        )
        rows.append(
            {
                "period_id": row.get("period_id"),
                "start_date": row.get("start_date"),
                "end_date": row.get("end_date"),
                "calendar_days": row.get("calendar_days"),
                "period_level": row.get("period_level"),
                "dominant_risk_reason": row.get("dominant_risk_reason"),
                "mechanisms": ", ".join(tags),
                "summary": row.get("period_summary"),
                "what_is_happening": what_is_happening_period(row),
                "science_rationale": science_rationale_period(row),
                "science_references": science_references_for_tags(tags, reason=reason),
                "evidence": evidence,
                "suggested_action": period_recommendation(row),
            }
        )
    return pd.DataFrame(rows)


def write_period_markdown(feedback: pd.DataFrame, output_path: Path) -> None:
    lines = [
        "# Athlete Risk Period Feedback",
        "",
        "These summaries describe sustained high-risk stretches rather than isolated days. Narratives are grounded in `SCIENTIFIC_RATIONALE.md` (ACWR, HRV/readiness, monotony/strain, sport-specific load, preparedness mismatch).",
        "",
    ]
    for _, row in feedback.iterrows():
        lines.extend(
            [
                f"## {row['start_date']} to {row['end_date']}",
                "",
                f"**Period level:** {row['period_level']} ({row['calendar_days']} calendar days)",
                "",
                f"**Summary:** {row['summary']}",
                "",
                f"**What is happening:** {row['what_is_happening']}",
                "",
                f"**Mechanisms:** {row['mechanisms']}",
                "",
                f"**Science rationale:** {row['science_rationale']}",
                "",
                f"**References:** {row['science_references']}",
                "",
                f"**Evidence:** {row['evidence']}",
                "",
                f"**Suggested action:** {row['suggested_action']}",
                "",
            ]
        )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def bone_stress_summary(row: pd.Series) -> str:
    reason = str(row.get("bone_stress_risk_reason", ""))
    if reason == "sustained high running volume":
        return "This looks like sustained high running volume that may outpace bone-tissue recovery capacity."
    if reason == "running volume progression":
        return (
            "Recent running exposure is ramping faster than your longer-term baseline — "
            "a load-progression pattern linked to bone-stress risk even when individual runs stay easy."
        )
    if reason == "running monotony block":
        return "This looks like repeated running with too little variation or rest days — a monotony pattern linked to overuse risk."
    if reason == "running while under-recovered":
        return "Running load occurred while recovery markers were already suppressed."
    if reason == "running load spike":
        return "This looks like a single-day running load spike relative to your recent baseline."
    if reason == "elevated running workload ratio":
        return "Recent running load is high relative to your longer-term running baseline (ACWR-style signal)."
    if reason == "elevated running intensity block":
        return "Running speed and internal load are genuinely elevated, not just total distance."
    if reason == "hard running session":
        return "This looks like a hard running session (training effect / HR / speed), not just a volume ramp."
    return "Running bone-stress context is currently low."


def what_is_happening_bone_stress(row: pd.Series) -> str:
    run7 = numeric_value(row.get("running_7d_sum_m"))
    run28 = numeric_value(row.get("running_28d_sum_m"))
    carryover = numeric_value(row.get("bone_stress_carryover_score"))
    accumulated = numeric_value(row.get("accumulated_bone_stress_state"))
    daily_dist = numeric_value(row.get("running_distance"))
    daily_dur = numeric_value(row.get("running_duration"))
    speed = numeric_value(row.get("running_avg_speed"))
    if daily_dist and daily_dur and daily_dur > 0:
        implied_speed = daily_dist / daily_dur
        if speed is None or speed < 1.5:
            speed = implied_speed
    max_speed = numeric_value(row.get("running_max_speed"))
    aerobic = numeric_value(row.get("running_aerobic_te"))
    anaerobic = numeric_value(row.get("running_anaerobic_te"))
    parts = []
    if run7:
        parts.append(f"7-day running total {fmt(run7 / 1000, 1)} km")
    if run28:
        parts.append(f"28-day running total {fmt(run28 / 1000, 1)} km")
    if speed:
        parts.append(f"avg speed {fmt(speed, 2)} m/s")
    if max_speed and max_speed > (speed or 0):
        parts.append(f"max speed {fmt(max_speed, 2)} m/s")
    if aerobic and aerobic > 0:
        parts.append(f"aerobic training effect {fmt(aerobic, 1)}")
    if anaerobic and anaerobic > 0:
        parts.append(f"anaerobic training effect {fmt(anaerobic, 1)}")
    load_story = sport_load_story(row)
    if load_story != "without a clearly dominant sport-specific load signal":
        parts.append(load_story)
    narrative = ". ".join(parts) if parts else "Running load signals were limited on this day."
    if accumulated is not None:
        narrative += f" Accumulated bone-stress state was {fmt(accumulated, 1)}."
    if carryover and carryover >= 45:
        narrative += f" Carryover from recent running blocks remains elevated ({fmt(carryover, 1)} over the last 21 days)."
    return narrative


def science_rationale_bone_stress(row: pd.Series) -> str:
    reason = str(row.get("bone_stress_risk_reason", ""))
    parts = [
        "Bone-stress monitoring is intentionally running-only: cycling and other sports do not dilute this track.",
        "BSI risk reflects loading cycles (volume), loading magnitude (speed/intensity), and how fast load rises [8,9].",
        "Wearable speed, heart rate, and Garmin training-effect scores are imperfect proxies for tissue-level bone load [7,8].",
    ]
    if reason in {"running monotony block", "sustained high running volume"}:
        parts.append("Foster's monotony framework is relevant when high running repeats without enough easy or off days [5].")
    if reason in {"running volume progression", "elevated running workload ratio"}:
        parts.append(
            "A rising acute:chronic running-load ratio and rapid volume progression are common monitoring features "
            "in load-injury literature, though they are not a diagnosis [1,2,8,10]."
        )
    if reason in {"elevated running intensity block", "hard running session"}:
        parts.append("Napier et al. emphasize progressing duration before intensity because BSI risk rises faster with speed than volume alone [8,9].")
    parts.append("This is preparedness monitoring for running tissue stress, not a bone-injury prediction model.")
    return " ".join(parts)


def bone_stress_recommendation(row: pd.Series) -> str:
    reason = str(row.get("bone_stress_risk_reason", ""))
    level = str(row.get("bone_stress_risk_level", ""))
    if level == "high" and reason in {"sustained high running volume", "running monotony block"}:
        return "Reduce running volume and add rest or cross-training days until 7-day and 28-day running totals trend down."
    if level == "high" and reason == "running volume progression":
        return "Hold running volume steady or step back for a week before adding more distance; prioritize easy aerobic pace."
    if level == "high" and reason in {"elevated running intensity block", "hard running session"}:
        return "Reduce running intensity and hard workouts before adding more volume; prioritize easy aerobic running until load scores fall."
    if level == "high" and reason == "running while under-recovered":
        return "Avoid hard or long runs until readiness rebounds; use lower-impact alternatives if you need aerobic work."
    if level == "high":
        return "Treat this as a running-load caution day even if general recovery risk looks moderate."
    if level == "moderate":
        return "Watch weekly running totals and spacing of hard days; avoid stacking long runs back-to-back."
    return "Running load appears within a tolerable bone-stress monitoring range for now."


def build_bone_stress_feedback(rows: pd.DataFrame) -> pd.DataFrame:
    output = []
    for _, row in rows.iterrows():
        reason = str(row.get("bone_stress_risk_reason", ""))
        evidence = (
            f"Bone-stress score {fmt(row.get('bone_stress_risk_score'), 1)} ({row.get('bone_stress_risk_level')}); "
            f"7-day load score {fmt(row.get('running_7d_load_score'), 1)}; "
            f"28-day load score {fmt(row.get('running_28d_load_score'), 1)}; "
            f"progression score {fmt(row.get('running_progression_score'), 1)}; "
            f"intensity score {fmt(row.get('running_intensity_score'), 1)}; "
            f"workout score {fmt(row.get('running_workout_score'), 1)}; "
            f"running monotony {fmt(row.get('running_monotony_score'), 1)}; "
            f"accumulated bone-stress state {fmt(row.get('accumulated_bone_stress_state'), 1)}; "
            f"21-day carryover {fmt(row.get('bone_stress_carryover_score'), 1)}."
        )
        refs = " · ".join(
            [
                SCIENTIFIC_REFERENCES["acwr"],
                SCIENTIFIC_REFERENCES["monotony"],
                SCIENTIFIC_REFERENCES["running_load"],
                "Napier et al. (2021) [8]; Edwards et al. (2010) [9] — speed/magnitude vs volume in BSI monitoring",
            ]
        )
        output.append(
            {
                "date": row.get("date"),
                "bone_stress_risk_score": row.get("bone_stress_risk_score"),
                "bone_stress_risk_level": row.get("bone_stress_risk_level"),
                "bone_stress_risk_reason": reason,
                "summary": bone_stress_summary(row),
                "what_is_happening": what_is_happening_bone_stress(row),
                "science_rationale": science_rationale_bone_stress(row),
                "science_references": refs,
                "evidence": evidence,
                "suggested_action": bone_stress_recommendation(row),
            }
        )
    return pd.DataFrame(output)


def bone_stress_period_mechanism_tags(row: pd.Series) -> list[str]:
    tags: list[str] = []
    mean_load = numeric_value(row.get("mean_running_7d_load_score")) or 0.0
    mean_intensity = numeric_value(row.get("mean_running_intensity_score")) or 0.0
    mean_progression = numeric_value(row.get("mean_running_progression_score")) or 0.0
    high_days = numeric_value(row.get("high_bone_stress_days")) or 0.0
    peak_run7 = numeric_value(row.get("peak_running_7d_km")) or 0.0
    if peak_run7 >= 120:
        tags.append("sustained high running volume")
    if mean_progression >= 65:
        tags.append("running volume progression")
    if mean_intensity >= 70:
        tags.append("elevated running intensity block")
    if mean_load >= 80:
        tags.append("sustained composite running load")
    if high_days == 0 and numeric_value(row.get("peak_accumulated_bone_stress_state")) or 0 >= 60:
        tags.append("chronic bone-stress accumulation without daily spikes")
    reason = str(row.get("dominant_bone_stress_reason", ""))
    if reason == "running monotony block":
        tags.append("running monotony")
    if reason == "running volume progression":
        tags.append("running volume progression")
    return tags or ["sustained running bone-stress load"]


def what_is_happening_bone_stress_period(row: pd.Series) -> str:
    start = row.get("start_date")
    end = row.get("end_date")
    days = row.get("calendar_days")
    peak = numeric_value(row.get("peak_accumulated_bone_stress_state"))
    mean_state = numeric_value(row.get("mean_accumulated_bone_stress_state"))
    high_days = numeric_value(row.get("high_bone_stress_days")) or 0
    peak_run7 = numeric_value(row.get("peak_running_7d_km"))
    tags = bone_stress_period_mechanism_tags(row)
    run_clause = f" Peak 7-day running total reached {fmt(peak_run7, 0)} km." if peak_run7 else ""
    return (
        f"From {start} to {end} ({days} days), accumulated bone-stress load stayed elevated "
        f"(peak state {fmt(peak, 1)}, mean {fmt(mean_state, 1)}) with {int(high_days)} high day(s). "
        f"Mechanisms: {', '.join(tags)}.{run_clause}"
    )


def science_rationale_bone_stress_period(row: pd.Series) -> str:
    tags = bone_stress_period_mechanism_tags(row)
    parts = [
        "Bone-stress periods track running-only repetitive loading, where tissue adaptation can lag cardiorespiratory fitness [8,10].",
    ]
    if "running volume progression" in tags:
        parts.append(
            "Rapid volume progression can raise bone-stress risk before cardiorespiratory fitness adapts; "
            "monitor acute:chronic load ratios during ramps [1,2,8,10]."
        )
    if "sustained high running volume" in tags or "sustained composite running load" in tags:
        parts.append("Sustained volume increases loading cycles; Napier et al. recommend monitoring cumulative running workload [8].")
    if "elevated running intensity block" in tags:
        parts.append("Speed and workout intensity raise loading magnitude faster than volume alone [8,9].")
    if "running monotony" in tags:
        parts.append("Repeated running without enough easy/off variation contributes to monotony-related strain [5,8].")
    if "chronic bone-stress accumulation without daily spikes" in tags:
        parts.append(
            "This pattern resembles a mesocycle block: accumulated state rose even when individual days did not all flag high."
        )
    parts.append("Period detection uses decaying accumulated bone-stress state, not isolated daily scores.")
    return " ".join(parts)


def bone_stress_period_recommendation(row: pd.Series) -> str:
    reason = str(row.get("dominant_bone_stress_reason", ""))
    if reason in {"running monotony block", "sustained high running volume"}:
        return "Reduce running volume, add rest or cross-training days, and avoid stacking hard run days until accumulated state trends down."
    if reason == "running volume progression":
        return "Hold or reduce weekly running distance for one to two weeks before progressing again; keep intensity easy."
    if reason in {"elevated running intensity block", "hard running session"}:
        return "Lower running intensity and limit hard workouts before adding more volume."
    if row.get("period_level") == "high":
        return "Treat this as a sustained running-load caution block, not a single bad day."
    return "Keep running conservative until accumulated bone-stress state falls below moderate levels."


def build_bone_stress_period_feedback(period_rows: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in period_rows.iterrows():
        tags = bone_stress_period_mechanism_tags(row)
        reason = str(row.get("dominant_bone_stress_reason", ""))
        evidence = (
            f"Peak accumulated state {fmt(row.get('peak_accumulated_bone_stress_state'), 1)}; "
            f"mean accumulated state {fmt(row.get('mean_accumulated_bone_stress_state'), 1)}; "
            f"elevated days {fmt(row.get('elevated_days'), 0)}; "
            f"high bone-stress days {fmt(row.get('high_bone_stress_days'), 0)}; "
            f"peak 7-day running {fmt(row.get('peak_running_7d_km'), 0)} km; "
            f"mean 7-day running {fmt(row.get('mean_running_7d_km'), 0)} km."
        )
        rows.append(
            {
                "period_id": row.get("period_id"),
                "start_date": row.get("start_date"),
                "end_date": row.get("end_date"),
                "calendar_days": row.get("calendar_days"),
                "period_level": row.get("period_level"),
                "dominant_bone_stress_reason": reason,
                "mechanisms": ", ".join(tags),
                "summary": row.get("period_summary"),
                "what_is_happening": what_is_happening_bone_stress_period(row),
                "science_rationale": science_rationale_bone_stress_period(row),
                "science_references": "[5,8,9,10]",
                "evidence": evidence,
                "suggested_action": bone_stress_period_recommendation(row),
            }
        )
    return pd.DataFrame(rows)


def write_bone_stress_period_markdown(feedback: pd.DataFrame, output_path: Path) -> None:
    lines = [
        "# Bone-Stress Period Feedback",
        "",
        "Multi-week running load blocks detected from accumulated bone-stress state. Not a medical diagnosis.",
        "",
    ]
    for _, row in feedback.iterrows():
        lines.extend(
            [
                f"## {row['start_date']} → {row['end_date']}",
                "",
                f"**Period level:** {row['period_level']} ({row['calendar_days']} calendar days)",
                "",
                f"**Summary:** {row['summary']}",
                "",
                f"**What is happening:** {row['what_is_happening']}",
                "",
                f"**Science rationale:** {row['science_rationale']}",
                "",
                f"**Suggested action:** {row['suggested_action']}",
                "",
            ]
        )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def write_bone_stress_markdown(feedback: pd.DataFrame, output_path: Path) -> None:
    lines = [
        "# Bone-Stress Running Risk Feedback",
        "",
        "Parallel running-only monitoring track for repetitive weight-bearing load. Separate from general preparedness risk and not a medical diagnosis.",
        "",
    ]
    for _, row in feedback.iterrows():
        lines.extend(
            [
                f"## {row['date']}",
                "",
                f"**Summary:** {row['summary']}",
                "",
                f"**What is happening:** {row['what_is_happening']}",
                "",
                f"**Science rationale:** {row['science_rationale']}",
                "",
                f"**References:** {row['science_references']}",
                "",
                f"**Evidence:** {row['evidence']}",
                "",
                f"**Suggested action:** {row['suggested_action']}",
                "",
            ]
        )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate athlete-facing feedback from embedding anomalies.")
    parser.add_argument("--anomalies", type=Path, default=Path("outputs/analysis/top_embedding_anomalies.csv"))
    parser.add_argument("--risk-days", type=Path, default=Path("outputs/analysis/top_risk_days.csv"))
    parser.add_argument("--risk-scores", type=Path, default=Path("outputs/analysis/athlete_risk_scores.csv"))
    parser.add_argument("--risk-periods", type=Path, default=Path("outputs/analysis/top_risk_periods.csv"))
    parser.add_argument("--bone-stress-days", type=Path, default=Path("outputs/analysis/top_bone_stress_days.csv"))
    parser.add_argument("--bone-stress-scores", type=Path, default=Path("outputs/analysis/athlete_bone_stress_scores.csv"))
    parser.add_argument("--bone-stress-periods", type=Path, default=Path("outputs/analysis/top_bone_stress_periods.csv"))
    parser.add_argument("--embeddings", type=Path, default=Path("outputs/modeling/pretrained_embeddings.csv"))
    parser.add_argument("--daily-features", type=Path, default=Path("data/processed/daily_features_with_fit_deduped.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/analysis"))
    parser.add_argument("--baseline-days", type=int, default=28)
    parser.add_argument("--top-n", type=int, default=10)
    args = parser.parse_args()

    anomalies = pd.read_csv(args.anomalies, parse_dates=["date"]).head(args.top_n)
    full_frame = load_context_frame(args.embeddings, args.daily_features)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    feedback = build_feedback(anomalies, full_frame, baseline_days=args.baseline_days)
    feedback.to_csv(args.output_dir / "athlete_feedback.csv", index=False)
    feedback.to_json(args.output_dir / "athlete_feedback.json", orient="records", indent=2)
    write_markdown(feedback, args.output_dir / "athlete_feedback.md")
    if args.risk_days.exists():
        risk_rows = pd.read_csv(args.risk_days).head(args.top_n)
        if args.risk_scores.exists():
            full_scores = pd.read_csv(args.risk_scores)
            risk_rows = risk_rows.drop(columns=["accumulated_risk_state", "daily_strain_contribution", "accumulated_risk_level"], errors="ignore")
            risk_rows = risk_rows.merge(full_scores[["date", "accumulated_risk_state", "daily_strain_contribution", "accumulated_risk_level"]], on="date", how="left")
        risk_feedback = build_risk_feedback(risk_rows)
        risk_feedback.to_csv(args.output_dir / "athlete_risk_feedback.csv", index=False)
        risk_feedback.to_json(args.output_dir / "athlete_risk_feedback.json", orient="records", indent=2)
        write_risk_markdown(risk_feedback, args.output_dir / "athlete_risk_feedback.md")
    if args.risk_periods.exists():
        period_rows = pd.read_csv(args.risk_periods).head(args.top_n)
        period_feedback = build_period_feedback(period_rows)
        period_feedback.to_csv(args.output_dir / "athlete_risk_period_feedback.csv", index=False)
        period_feedback.to_json(args.output_dir / "athlete_risk_period_feedback.json", orient="records", indent=2)
        write_period_markdown(period_feedback, args.output_dir / "athlete_risk_period_feedback.md")
    if args.bone_stress_days.exists():
        bone_rows = pd.read_csv(args.bone_stress_days).head(args.top_n)
        if args.bone_stress_scores.exists():
            full_bone = pd.read_csv(args.bone_stress_scores)
            extra_cols = [
                "running_distance",
                "running_avg_speed",
                "running_max_speed",
                "running_aerobic_te",
                "running_anaerobic_te",
                "previous_day_running_distance",
            ]
            merge_cols = ["date"] + [c for c in extra_cols if c in full_bone.columns]
            bone_rows = bone_rows.merge(full_bone[merge_cols], on="date", how="left", suffixes=("", "_full"))
        bone_feedback = build_bone_stress_feedback(bone_rows)
        bone_feedback.to_csv(args.output_dir / "athlete_bone_stress_feedback.csv", index=False)
        bone_feedback.to_json(args.output_dir / "athlete_bone_stress_feedback.json", orient="records", indent=2)
        write_bone_stress_markdown(bone_feedback, args.output_dir / "athlete_bone_stress_feedback.md")
    if args.bone_stress_periods.exists():
        bone_period_rows = pd.read_csv(args.bone_stress_periods).head(args.top_n)
        bone_period_feedback = build_bone_stress_period_feedback(bone_period_rows)
        bone_period_feedback.to_csv(args.output_dir / "athlete_bone_stress_period_feedback.csv", index=False)
        bone_period_feedback.to_json(args.output_dir / "athlete_bone_stress_period_feedback.json", orient="records", indent=2)
        write_bone_stress_period_markdown(bone_period_feedback, args.output_dir / "athlete_bone_stress_period_feedback.md")
    print(f"Wrote athlete feedback outputs to {args.output_dir}")


if __name__ == "__main__":
    main()
