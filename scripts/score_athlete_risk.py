"""Score athlete-state risk separately from embedding novelty."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / "outputs" / ".matplotlib"))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.bone_stress_literature import (
    absolute_acwr_risk,
    absolute_edwards_speed_risk,
    absolute_running_volume_risk,
    acwr_zone_label,
    edwards_speed_band,
    foster_monotony_risk,
    foster_monotony_strain,
    is_edwards_hard_running_session,
    literature_bone_stress_score,
    monitoring_agreement,
    risk_level as literature_risk_level,
)
from src.counterfactual_simulator import enrich_counterfactual_scenarios
from src.embedding_explanations import enrich_embedding_explanations
from src.frontier_attribution import enrich_frontier_attribution
from src.frontier_monitoring import enrich_frontier_monitoring
from src.garmin_pipeline import load_summarized_running_daily
from src.operational_alerts import counterfactual_hint, operational_alert_tier, tier_label, tier_recommendation


COLUMN_CANDIDATES = {
    "readiness": ["readiness_score"],
    "hrv": ["readiness_hrvWeeklyAverage"],
    "resting_hr": ["wellness_restingHeartRate", "wellness_currentDayRestingHeartRate"],
    "sleep": ["sleep_total_seconds", "sleep_total_in_bed_seconds"],
    "body_battery_charged": ["wellness_bodyBattery_chargedValue"],
    "body_battery_drained": ["wellness_bodyBattery_drainedValue"],
    "load": ["load_dailyTrainingLoadAcute", "readiness_acuteLoad", "activity_training_load"],
    "duration": ["activity_duration_seconds"],
    "distance": ["activity_distance_m"],
    "activity_count": ["activity_count"],
    "running_duration": ["running_duration_seconds"],
    "running_distance": ["running_distance_m"],
    "cycling_duration": ["cycling_duration_seconds"],
    "cycling_distance": ["cycling_distance_m"],
    "hiking_duration": ["hiking_duration_seconds"],
    "hiking_distance": ["hiking_distance_m"],
    "impact_duration": ["impact_weighted_duration_seconds"],
    "impact_distance": ["impact_weighted_distance_m"],
    "fatigue_duration": ["fatigue_weighted_duration_seconds"],
}

BONE_STRESS_COLUMN_CANDIDATES = {
    "running_avg_speed": ["running_avg_speed"],
    "running_max_speed": ["running_max_speed"],
    "running_avg_hr": ["running_avg_hr"],
    "running_max_hr": ["running_max_hr"],
    "running_elevation_gain": ["running_elevation_gain"],
    "running_aerobic_te": ["running_aerobic_training_effect"],
    "running_anaerobic_te": ["running_anaerobic_training_effect"],
    "running_activity_count": ["running_activity_count"],
}

# Literature-informed composite load weights (Napier et al. 2021; Edwards et al. 2010).
BONE_LOAD_WEIGHTS = {
    "distance": 1.0,
    "speed_duration": 0.45,
    "elevation": 1.0,
    "aerobic_te": 2500.0,
    "anaerobic_te": 5000.0,
    "hr_duration": 30.0,
}

# Cap implausible running distance from duplicate FIT exports or misclassified activities.
MAX_RUNNING_SPEED_MPS = 6.5  # ~23 km/h; spring 2024 real runs stay under ~4.2 m/s implied.


def sanitize_running_distance(distance: object, duration: object) -> float:
    """Limit daily running distance to what duration allows at a generous max speed."""
    dist = pd.to_numeric(distance, errors="coerce")
    dur = pd.to_numeric(duration, errors="coerce")
    if pd.isna(dist) or dist <= 0:
        return 0.0
    if pd.isna(dur) or dur <= 0:
        return float(dist)
    return float(min(dist, dur * MAX_RUNNING_SPEED_MPS))


def apply_running_distance_sanity(frame: pd.DataFrame) -> pd.DataFrame:
    enriched = frame.copy()
    sanitized = [
        sanitize_running_distance(row.get("running_distance"), row.get("running_duration"))
        for _, row in enriched.iterrows()
    ]
    enriched["running_distance_raw"] = pd.to_numeric(enriched["running_distance"], errors="coerce")
    enriched["running_distance"] = sanitized
    return enriched


def apply_json_running_corrections(frame: pd.DataFrame, raw_dir: Path | None) -> pd.DataFrame:
    """Prefer Garmin summarizedActivities JSON for running volume when available."""
    enriched = frame.copy()
    if raw_dir is None or not raw_dir.exists():
        return enriched

    json_daily = load_summarized_running_daily(raw_dir)
    if json_daily.empty:
        return enriched

    enriched["date"] = pd.to_datetime(enriched["date"]).dt.normalize()
    enriched = enriched.merge(json_daily, on="date", how="left")
    json_dist = pd.to_numeric(enriched["running_distance_json_m"], errors="coerce")
    json_dur = pd.to_numeric(enriched["running_duration_json_s"], errors="coerce")
    csv_dist = pd.to_numeric(enriched["running_distance"], errors="coerce")
    csv_dur = pd.to_numeric(enriched["running_duration"], errors="coerce")
    enriched["running_distance"] = np.where(json_dist.notna(), json_dist, csv_dist)
    enriched["running_duration"] = np.where(json_dur.notna(), json_dur, csv_dur)

    dist = pd.to_numeric(enriched["running_distance"], errors="coerce").fillna(0)
    dur = pd.to_numeric(enriched["running_duration"], errors="coerce").fillna(0)
    implied_speed = np.where(dur > 0, dist / dur, np.nan)
    enriched["running_avg_speed"] = implied_speed
    return enriched.drop(columns=["running_distance_json_m", "running_duration_json_s"], errors="ignore")


def first_available(frame: pd.DataFrame, candidates: list[str]) -> str | None:
    return next((column for column in candidates if column in frame.columns), None)


def value_or_none(value: object) -> float | None:
    if pd.isna(value):
        return None
    return float(value)


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return float(max(low, min(high, value)))


def percentile_score(history: pd.Series, value: object, direction: str) -> float:
    """Return risk score from a rolling percentile.

    direction="high" means high values are risky; direction="low" means low values
    are risky. Missing or short history returns 0 rather than inventing risk.
    """
    if pd.isna(value):
        return 0.0
    observed = pd.to_numeric(history, errors="coerce").dropna()
    if len(observed) < 7:
        return 0.0
    percentile = float((observed <= float(value)).mean() * 100)
    return clamp(percentile if direction == "high" else 100.0 - percentile)


def absolute_readiness_risk(value: object) -> float:
    if pd.isna(value):
        return 0.0
    value = float(value)
    if value <= 20:
        return 100.0
    if value <= 35:
        return 80.0
    if value <= 50:
        return 55.0
    return 0.0


def blended_risk_score(percentile: float, absolute: float, relative_weight: float = 0.45) -> float:
    """Combine individualized percentiles with absolute tissue-load anchors [8,10]."""
    return clamp(relative_weight * percentile + (1.0 - relative_weight) * absolute)


def absolute_running_workout_risk(aerobic_te: object, anaerobic_te: object) -> float:
    """Garmin training-effect scale: easy aerobic work stays low even if relatively elevated."""
    aer = 0.0 if pd.isna(aerobic_te) else float(aerobic_te)
    ana = 0.0 if pd.isna(anaerobic_te) else float(anaerobic_te)
    aer_risk = clamp((aer - 1.75) / 2.0 * 100.0)
    ana_risk = clamp(ana / 1.5 * 100.0)
    return clamp(max(aer_risk, ana_risk * 1.05))


def absolute_running_intensity_risk(
    speed: object,
    max_speed: object,
    aerobic_te: object,
    anaerobic_te: object,
) -> float:
    """Edwards speed bands with Garmin TE as secondary proxy [8,9]."""
    spd = 0.0 if pd.isna(speed) else float(speed)
    mx = 0.0 if pd.isna(max_speed) else float(max_speed)
    peak_speed = max(spd, mx * 0.85) if mx > 1.5 else spd
    edwards = absolute_edwards_speed_risk(peak_speed)
    return clamp(max(edwards, absolute_running_workout_risk(aerobic_te, anaerobic_te) * 0.35))


def running_progression_risk(
    acwr: object,
    volume_percentile_7d: float,
    load_percentile_7d: float,
    km_7d: object,
) -> float:
    """Rapid running-volume ramp relative to chronic load [1,2,8,10]."""
    relative = clamp(0.55 * volume_percentile_7d + 0.45 * load_percentile_7d)
    absolute = clamp(0.65 * absolute_acwr_risk(acwr) + 0.35 * absolute_running_volume_risk(km_7d))
    return blended_risk_score(relative, absolute, relative_weight=0.50)


def volume_context_factor(absolute_volume: float) -> float:
    """Scale contextual strain by absolute weekly running exposure [8]."""
    return clamp(0.40 + 0.60 * absolute_volume / 100.0)


def bone_stress_severity_score(
    risk_score: float,
    load_7d: float,
    load_28d: float,
    workout_score: float,
    genuine_hard_session: bool,
) -> float:
    """Rank days by absolute load first, then session hardness."""
    session_component = workout_score if genuine_hard_session else workout_score * 0.35
    return clamp(0.45 * load_7d + 0.25 * load_28d + 0.15 * session_component + 0.15 * risk_score)


def rolling_history(frame: pd.DataFrame, idx: int, days: int) -> pd.DataFrame:
    date = frame.iloc[idx]["date"]
    start = date - pd.Timedelta(days=days)
    return frame[(frame["date"] < date) & (frame["date"] >= start)]


def rolling_sum_score(frame: pd.DataFrame, idx: int, column: str, days: int, baseline_days: int) -> float:
    current_date = frame.iloc[idx]["date"]
    current_start = current_date - pd.Timedelta(days=days)
    current_sum = pd.to_numeric(
        frame.loc[(frame["date"] < current_date) & (frame["date"] >= current_start), column],
        errors="coerce",
    ).sum()
    history_start = current_date - pd.Timedelta(days=baseline_days + days)
    historical = frame.loc[(frame["date"] < current_date) & (frame["date"] >= history_start), ["date", column]].copy()
    if len(historical) < days * 2:
        return 0.0
    historical = historical.set_index("date").sort_index()
    rolling_sums = pd.to_numeric(historical[column], errors="coerce").rolling(f"{days}D").sum().dropna()
    rolling_sums = rolling_sums[rolling_sums.index < current_start]
    return percentile_score(rolling_sums, current_sum, "high")


def rolling_mean_score(frame: pd.DataFrame, idx: int, column: str, days: int, baseline_days: int) -> float:
    current_date = frame.iloc[idx]["date"]
    current_start = current_date - pd.Timedelta(days=days)
    current_mean = pd.to_numeric(
        frame.loc[(frame["date"] < current_date) & (frame["date"] >= current_start), column],
        errors="coerce",
    ).mean()
    if pd.isna(current_mean):
        return 0.0
    history_start = current_date - pd.Timedelta(days=baseline_days + days)
    historical = frame.loc[(frame["date"] < current_date) & (frame["date"] >= history_start), ["date", column]].copy()
    if len(historical) < days * 2:
        return 0.0
    historical = historical.set_index("date").sort_index()
    rolling_means = pd.to_numeric(historical[column], errors="coerce").rolling(f"{days}D").mean().dropna()
    rolling_means = rolling_means[rolling_means.index < current_start]
    return percentile_score(rolling_means, current_mean, "high")


def map_canonical_columns(frame: pd.DataFrame, extra_candidates: dict[str, list[str]] | None = None) -> pd.DataFrame:
    mapped = frame.copy()
    candidates = COLUMN_CANDIDATES.copy()
    if extra_candidates:
        candidates.update(extra_candidates)
    for canonical, options in candidates.items():
        source = first_available(mapped, options)
        mapped[canonical] = pd.to_numeric(mapped[source], errors="coerce") if source else np.nan
    return mapped


def compute_running_bone_stress_load(frame: pd.DataFrame) -> pd.Series:
    """Composite running load: volume + speed/magnitude + workouts + internal HR load."""
    distance = pd.to_numeric(frame["running_distance"], errors="coerce").fillna(0)
    duration = pd.to_numeric(frame["running_duration"], errors="coerce").fillna(0)
    speed = pd.to_numeric(frame.get("running_avg_speed", 0), errors="coerce").fillna(0)
    max_speed = pd.to_numeric(frame.get("running_max_speed", 0), errors="coerce").fillna(0)
    elevation = pd.to_numeric(frame.get("running_elevation_gain", 0), errors="coerce").fillna(0)
    aerobic_te = pd.to_numeric(frame.get("running_aerobic_te", 0), errors="coerce").fillna(0)
    anaerobic_te = pd.to_numeric(frame.get("running_anaerobic_te", 0), errors="coerce").fillna(0)
    avg_hr = pd.to_numeric(frame.get("running_avg_hr", 0), errors="coerce").fillna(0)
    speed_factor = np.maximum(speed, max_speed * 0.85)
    return (
        distance * BONE_LOAD_WEIGHTS["distance"]
        + duration * speed_factor * BONE_LOAD_WEIGHTS["speed_duration"]
        + elevation * BONE_LOAD_WEIGHTS["elevation"]
        + aerobic_te * BONE_LOAD_WEIGHTS["aerobic_te"]
        + anaerobic_te * BONE_LOAD_WEIGHTS["anaerobic_te"]
        + avg_hr * duration / 3600.0 * BONE_LOAD_WEIGHTS["hr_duration"]
    )


def enrich_running_bone_stress_features(frame: pd.DataFrame, raw_dir: Path | None = None) -> pd.DataFrame:
    enriched = map_canonical_columns(frame, BONE_STRESS_COLUMN_CANDIDATES)
    enriched = apply_running_distance_sanity(enriched)
    enriched = apply_json_running_corrections(enriched, raw_dir)
    enriched = apply_running_distance_sanity(enriched)
    dist = pd.to_numeric(enriched["running_distance"], errors="coerce").fillna(0)
    dur = pd.to_numeric(enriched["running_duration"], errors="coerce").fillna(0)
    enriched["running_avg_speed"] = np.where(dur > 0, dist / dur, np.nan)
    enriched["running_bone_stress_load"] = compute_running_bone_stress_load(enriched)
    enriched = enriched.sort_values("date").set_index("date")
    load = pd.to_numeric(enriched["running_bone_stress_load"], errors="coerce").fillna(0)
    distance = pd.to_numeric(enriched["running_distance"], errors="coerce").fillna(0)
    enriched["running_7d_load_sum"] = load.rolling("7D").sum()
    enriched["running_28d_load_sum"] = load.rolling("28D").sum()
    enriched["running_7d_sum_m"] = distance.rolling("7D").sum()
    enriched["running_28d_sum_m"] = distance.rolling("28D").sum()
    enriched["running_7d_acwr"] = np.where(
        enriched["running_28d_load_sum"] > 0,
        4.0 * enriched["running_7d_load_sum"] / enriched["running_28d_load_sum"],
        np.nan,
    )
    return enriched.reset_index()


def compute_recovery_strain(frame: pd.DataFrame, idx: int, baseline_days: int) -> float:
    row = frame.iloc[idx]
    history = rolling_history(frame, idx, baseline_days)
    readiness_risk = max(
        absolute_readiness_risk(row["readiness"]),
        percentile_score(history["readiness"], row["readiness"], "low"),
    )
    hrv_risk = percentile_score(history["hrv"], row["hrv"], "low")
    resting_hr_risk = percentile_score(history["resting_hr"], row["resting_hr"], "high")
    sleep_risk = percentile_score(history["sleep"], row["sleep"], "low")
    body_battery_risk = max(
        percentile_score(history["body_battery_charged"], row["body_battery_charged"], "low"),
        percentile_score(history["body_battery_drained"], row["body_battery_drained"], "high"),
    )
    return clamp(
        0.45 * readiness_risk
        + 0.2 * hrv_risk
        + 0.15 * resting_hr_risk
        + 0.1 * sleep_risk
        + 0.1 * body_battery_risk
    )


def score_bone_stress_row(frame: pd.DataFrame, idx: int, baseline_days: int) -> dict[str, float | str | None]:
    """Running-centered bone-stress monitoring track, separate from general preparedness risk."""
    row = frame.iloc[idx]
    history = rolling_history(frame, idx, baseline_days)
    previous = frame.iloc[idx - 1] if idx > 0 else None
    recovery_strain = compute_recovery_strain(frame, idx, baseline_days)

    prior_running_score = 0.0
    if previous is not None:
        prior_running_score = max(
            percentile_score(history["running_bone_stress_load"], previous["running_bone_stress_load"], "high"),
            percentile_score(history["running_duration"], previous["running_duration"], "high"),
            percentile_score(history["running_distance"], previous["running_distance"], "high"),
        )

    run_under_recovered_score = clamp(
        max(
            percentile_score(history["running_duration"], row["running_duration"], "high"),
            percentile_score(history["running_distance"], row["running_distance"], "high"),
            percentile_score(history["running_bone_stress_load"], row["running_bone_stress_load"], "high"),
        )
        * recovery_strain
        / 100.0
    )

    running_7d_load_score = rolling_sum_score(
        frame, idx, "running_bone_stress_load", days=7, baseline_days=baseline_days
    )
    running_28d_load_score = rolling_sum_score(
        frame, idx, "running_bone_stress_load", days=28, baseline_days=max(baseline_days * 2, 56)
    )
    running_7d_volume_score = rolling_sum_score(frame, idx, "running_distance", days=7, baseline_days=baseline_days)
    running_28d_volume_score = rolling_sum_score(
        frame, idx, "running_distance", days=28, baseline_days=max(baseline_days * 2, 56)
    )
    load_7d_percentile = running_7d_load_score
    volume_7d_percentile = running_7d_volume_score
    acwr_percentile = percentile_score(history["running_7d_acwr"], row["running_7d_acwr"], "high")
    run7_m = pd.to_numeric(row.get("running_7d_sum_m"), errors="coerce")
    run7_km = float(run7_m) / 1000.0 if pd.notna(run7_m) else 0.0
    run28_km = pd.to_numeric(row.get("running_28d_sum_m"), errors="coerce")
    run28_km = float(run28_km) / 1000.0 if pd.notna(run28_km) else 0.0
    absolute_workout = absolute_running_workout_risk(row["running_aerobic_te"], row["running_anaerobic_te"])
    absolute_intensity = absolute_running_intensity_risk(
        row["running_avg_speed"],
        row["running_max_speed"],
        row["running_aerobic_te"],
        row["running_anaerobic_te"],
    )
    absolute_volume = absolute_running_volume_risk(run7_km)
    absolute_acwr = absolute_acwr_risk(row["running_7d_acwr"])

    running_7d_load_score = blended_risk_score(load_7d_percentile, absolute_volume)
    running_28d_load_score = blended_risk_score(
        running_28d_load_score,
        absolute_running_volume_risk(run28_km),
    )
    running_acwr_score = blended_risk_score(acwr_percentile, absolute_acwr)
    running_progression_score = running_progression_risk(
        row["running_7d_acwr"],
        volume_7d_percentile,
        load_7d_percentile,
        run7_km,
    )

    workout_percentile = clamp(
        max(
            percentile_score(history["running_aerobic_te"], row["running_aerobic_te"], "high"),
            percentile_score(history["running_anaerobic_te"], row["running_anaerobic_te"], "high") * 1.1,
        )
    )
    running_speed_score = max(
        percentile_score(history["running_avg_speed"], row["running_avg_speed"], "high"),
        percentile_score(history["running_max_speed"], row["running_max_speed"], "high"),
        rolling_mean_score(frame, idx, "running_avg_speed", days=7, baseline_days=baseline_days),
    )
    running_hr_score = max(
        percentile_score(history["running_avg_hr"], row["running_avg_hr"], "high"),
        percentile_score(history["running_max_hr"], row["running_max_hr"], "high"),
    )
    intensity_percentile = clamp(max(running_speed_score, running_hr_score * 0.85, workout_percentile * 0.85))
    running_workout_score = blended_risk_score(workout_percentile, absolute_workout)
    running_intensity_score = blended_risk_score(intensity_percentile, absolute_intensity)
    same_day_load_score = max(
        percentile_score(history["running_bone_stress_load"], row["running_bone_stress_load"], "high"),
        percentile_score(history["running_duration"], row["running_duration"], "high"),
        percentile_score(history["running_distance"], row["running_distance"], "high"),
    )
    week_start = row["date"] - pd.Timedelta(days=6)
    week_loads = frame.loc[(frame["date"] >= week_start) & (frame["date"] <= row["date"]), "running_bone_stress_load"]
    foster_monotony, foster_strain = foster_monotony_strain(week_loads)
    running_monotony = foster_monotony_risk(foster_monotony)
    volume_factor = volume_context_factor(absolute_volume)
    monotony_effective = clamp(running_monotony * volume_factor)
    daily_km = pd.to_numeric(row.get("running_distance"), errors="coerce")
    daily_km = float(daily_km) / 1000.0 if pd.notna(daily_km) else 0.0
    session_speed = pd.to_numeric(row.get("running_avg_speed"), errors="coerce")
    genuine_hard_session = is_edwards_hard_running_session(session_speed, daily_km)
    literature_score = literature_bone_stress_score(
        row["running_7d_acwr"],
        session_speed,
        run7_km,
        foster_monotony,
        foster_strain,
    )

    chronic_running_load = clamp(
        max(running_7d_load_score, running_28d_load_score * 0.9, prior_running_score, running_7d_volume_score * 0.85)
    )
    if monotony_effective >= 35:
        chronic_running_load = clamp(max(chronic_running_load, (running_7d_load_score + running_28d_load_score) / 2.0))

    load_with_suppressed_recovery = chronic_running_load * (0.3 + 0.7 * recovery_strain / 100.0)
    monotony_block = chronic_running_load * 0.65 if monotony_effective >= 45 else monotony_effective * 0.45
    acwr_spike = clamp(0.55 * running_acwr_score + 0.45 * running_7d_load_score)
    intensity_block = clamp(
        0.55 * running_intensity_score + 0.45 * running_workout_score
    ) * (0.35 + 0.65 * chronic_running_load / 100.0) * volume_factor
    personalized_score = clamp(
        0.25 * running_7d_load_score
        + 0.18 * running_28d_load_score
        + 0.15 * running_progression_score
        + 0.12 * running_intensity_score
        + 0.12 * running_workout_score
        + 0.10 * running_acwr_score
        + 0.08 * monotony_effective
    )

    bone_stress_risk_score = clamp(
        max(
            clamp(0.50 * literature_score + 0.50 * personalized_score),
            personalized_score,
            load_with_suppressed_recovery * 0.9,
            run_under_recovered_score,
            running_progression_score * 0.92,
            monotony_block * 0.85 if monotony_effective >= 50 else 0.0,
            acwr_spike * 0.85,
            intensity_block * 0.8 if absolute_intensity >= 50 and genuine_hard_session else 0.0,
            same_day_load_score * recovery_strain / 120.0,
        )
    )
    severity_score = bone_stress_severity_score(
        bone_stress_risk_score,
        running_7d_load_score,
        running_28d_load_score,
        running_workout_score,
        genuine_hard_session,
    )

    if pd.isna(run7_m) or run7_m < 1000:
        bone_stress_risk_score = min(bone_stress_risk_score, 15.0)
    elif (
        running_7d_load_score < 25
        and running_28d_load_score < 25
        and same_day_load_score < 25
        and running_intensity_score < 25
    ):
        bone_stress_risk_score = min(bone_stress_risk_score, 20.0)

    if bone_stress_risk_score >= 70:
        bone_stress_risk_level = "high"
    elif bone_stress_risk_score >= 45:
        bone_stress_risk_level = "moderate"
    else:
        bone_stress_risk_level = "low"

    volume_block = clamp(max(load_with_suppressed_recovery, chronic_running_load * 0.85, personalized_score))
    hard_session_score = clamp(0.6 * running_workout_score + 0.4 * running_intensity_score)
    if not genuine_hard_session:
        hard_session_score = 0.0
    progression_block = running_progression_score
    if absolute_workout < 50 and absolute_acwr >= 35:
        progression_block = clamp(max(progression_block, running_progression_score * 1.08))

    candidates = {
        "running while under-recovered": run_under_recovered_score,
        "sustained high running volume": volume_block if absolute_volume >= 55 else volume_block * 0.65,
        "running volume progression": progression_block,
        "running monotony block": monotony_block,
        "running load spike": max(same_day_load_score * recovery_strain / 100.0, prior_running_score * 0.9),
        "elevated running workload ratio": acwr_spike,
        "hard running session": hard_session_score,
        "elevated running intensity block": intensity_block if absolute_intensity >= 50 and genuine_hard_session else 0.0,
    }
    if bone_stress_risk_level == "low":
        bone_stress_risk_reason = "low running bone-stress context"
    else:
        ranked = sorted(candidates.items(), key=lambda item: item[1], reverse=True)
        bone_stress_risk_reason = ranked[0][0]
        if absolute_workout < 50 and absolute_volume < 70:
            progression_reasons = {
                "running volume progression",
                "running monotony block",
                "sustained high running volume",
                "elevated running workload ratio",
            }
            top_score = ranked[0][1]
            for reason, score in ranked:
                if reason in progression_reasons and score >= top_score * 0.85:
                    bone_stress_risk_reason = reason
                    break
        elif run7_km >= 85 and daily_km < run7_km / 5.0:
            volume_reasons = {
                "sustained high running volume",
                "running volume progression",
                "running monotony block",
            }
            top_score = ranked[0][1]
            for reason, score in ranked:
                if reason in volume_reasons and score >= top_score * 0.80:
                    bone_stress_risk_reason = reason
                    break

    return {
        "bone_stress_risk_score": bone_stress_risk_score,
        "literature_bone_stress_score": literature_score,
        "personalized_bone_stress_score": personalized_score,
        "literature_bone_stress_level": literature_risk_level(literature_score),
        "personalized_bone_stress_level": literature_risk_level(personalized_score),
        "running_acwr_zone": acwr_zone_label(row["running_7d_acwr"]),
        "running_edwards_speed_band": edwards_speed_band(session_speed) if pd.notna(session_speed) else "none",
        "foster_monotony": foster_monotony,
        "foster_strain": foster_strain,
        "bone_stress_severity_score": severity_score,
        "bone_stress_risk_level": bone_stress_risk_level,
        "bone_stress_risk_reason": bone_stress_risk_reason,
        "recovery_strain_score": recovery_strain,
        "running_7d_load_score": running_7d_load_score,
        "running_28d_load_score": running_28d_load_score,
        "running_7d_volume_score": running_7d_volume_score,
        "running_28d_volume_score": running_28d_volume_score,
        "running_intensity_score": running_intensity_score,
        "running_workout_score": running_workout_score,
        "running_acwr_score": running_acwr_score,
        "running_progression_score": running_progression_score,
        "running_monotony_score": running_monotony,
        "run_under_recovered_score": run_under_recovered_score,
        "running_7d_sum_m": value_or_none(row["running_7d_sum_m"]),
        "running_28d_sum_m": value_or_none(row["running_28d_sum_m"]),
        "running_7d_load_sum": value_or_none(row["running_7d_load_sum"]),
        "running_28d_load_sum": value_or_none(row["running_28d_load_sum"]),
        "running_avg_speed": value_or_none(row["running_avg_speed"]),
        "running_max_speed": value_or_none(row["running_max_speed"]),
        "running_aerobic_te": value_or_none(row["running_aerobic_te"]),
        "running_anaerobic_te": value_or_none(row["running_anaerobic_te"]),
        "running_distance": value_or_none(row["running_distance"]),
        "previous_day_running_distance": value_or_none(previous["running_distance"]) if previous is not None else None,
    }


def daily_bone_stress_contribution(row: pd.Series) -> float:
    """Running-only strain input for accumulated bone-stress state."""
    return clamp(
        0.22 * float(row["running_7d_load_score"])
        + 0.22 * float(row["running_28d_load_score"])
        + 0.15 * float(row["running_progression_score"])
        + 0.16 * float(row["running_intensity_score"])
        + 0.12 * float(row["running_workout_score"])
        + 0.13 * float(row["running_monotony_score"])
    )


def compute_accumulated_bone_stress_state(scores: pd.DataFrame, decay: float) -> pd.DataFrame:
    enriched = scores.copy()
    contributions = enriched.apply(daily_bone_stress_contribution, axis=1)
    carry = 0.0
    states: list[float] = []
    for contribution in contributions:
        carry = decay * carry + (1.0 - decay) * contribution
        states.append(clamp(carry))
    enriched["daily_bone_stress_contribution"] = contributions
    enriched["accumulated_bone_stress_state"] = states
    enriched["accumulated_bone_stress_level"] = enriched["accumulated_bone_stress_state"].map(
        lambda value: "high" if value >= 65 else "moderate" if value >= 45 else "low"
    )
    enriched["bone_stress_carryover_score"] = (
        enriched["accumulated_bone_stress_state"].rolling(window=21, min_periods=1).max().round(2)
    )
    return enriched


def load_daily_frame(daily_features_path: Path, raw_dir: Path | None = None) -> pd.DataFrame:
    daily = pd.read_csv(daily_features_path, parse_dates=["date"], low_memory=False)
    daily = daily.sort_values("date").reset_index(drop=True)
    return enrich_running_bone_stress_features(daily, raw_dir=raw_dir)


def score_bone_stress_history(frame: pd.DataFrame, baseline_days: int, bone_stress_decay: float) -> pd.DataFrame:
    rows = []
    for idx in range(len(frame)):
        result = score_bone_stress_row(frame, idx, baseline_days)
        result["date"] = frame.iloc[idx]["date"].date().isoformat()
        rows.append(result)
    scores = pd.DataFrame(rows)
    return compute_accumulated_bone_stress_state(scores, decay=bone_stress_decay)


def load_inputs(embeddings_path: Path, daily_features_path: Path, raw_dir: Path | None = None) -> pd.DataFrame:
    embeddings = pd.read_csv(embeddings_path, parse_dates=["date"])
    daily = pd.read_csv(daily_features_path, parse_dates=["date"], low_memory=False)
    frame = embeddings.merge(daily, on="date", how="left").sort_values("date").reset_index(drop=True)
    frame = map_canonical_columns(frame)
    frame["state_novelty_score"] = pd.to_numeric(frame.get("anomaly_zscore", 0), errors="coerce").fillna(0).clip(lower=0)
    # Put novelty roughly on the same 0-100 scale without letting it dominate risk.
    frame["state_novelty_score"] = (frame["state_novelty_score"] / frame["state_novelty_score"].quantile(0.95)).clip(upper=1) * 100
    return enrich_running_bone_stress_features(frame, raw_dir=raw_dir)


def score_row(frame: pd.DataFrame, idx: int, baseline_days: int) -> dict[str, float | str | None]:
    row = frame.iloc[idx]
    history = rolling_history(frame, idx, baseline_days)
    previous = frame.iloc[idx - 1] if idx > 0 else None
    recent_7 = rolling_history(frame, idx, 7)

    readiness_risk = max(
        absolute_readiness_risk(row["readiness"]),
        percentile_score(history["readiness"], row["readiness"], "low"),
    )
    hrv_risk = percentile_score(history["hrv"], row["hrv"], "low")
    resting_hr_risk = percentile_score(history["resting_hr"], row["resting_hr"], "high")
    sleep_risk = percentile_score(history["sleep"], row["sleep"], "low")
    body_battery_risk = max(
        percentile_score(history["body_battery_charged"], row["body_battery_charged"], "low"),
        percentile_score(history["body_battery_drained"], row["body_battery_drained"], "high"),
    )

    recovery_strain = clamp(
        0.45 * readiness_risk
        + 0.2 * hrv_risk
        + 0.15 * resting_hr_risk
        + 0.1 * sleep_risk
        + 0.1 * body_battery_risk
    )

    prior_load_score = prior_duration_score = prior_distance_score = 0.0
    prior_impact_score = prior_fatigue_score = prior_running_score = 0.0
    previous_day_load = previous_day_duration = previous_day_distance = None
    previous_day_impact_duration = previous_day_running_distance = previous_day_cycling_distance = None
    if previous is not None:
        previous_day_load = value_or_none(previous["load"])
        previous_day_duration = value_or_none(previous["duration"])
        previous_day_distance = value_or_none(previous["distance"])
        previous_day_impact_duration = value_or_none(previous["impact_duration"])
        previous_day_running_distance = value_or_none(previous["running_distance"])
        previous_day_cycling_distance = value_or_none(previous["cycling_distance"])
        prior_load_score = percentile_score(history["load"], previous["load"], "high")
        prior_duration_score = percentile_score(history["duration"], previous["duration"], "high")
        prior_distance_score = percentile_score(history["distance"], previous["distance"], "high")
        prior_impact_score = max(
            percentile_score(history["impact_duration"], previous["impact_duration"], "high"),
            percentile_score(history["impact_distance"], previous["impact_distance"], "high"),
        )
        prior_fatigue_score = percentile_score(history["fatigue_duration"], previous["fatigue_duration"], "high")
        prior_running_score = max(
            percentile_score(history["running_duration"], previous["running_duration"], "high"),
            percentile_score(history["running_distance"], previous["running_distance"], "high"),
        )
    recent_load_score = rolling_sum_score(frame, idx, "load", days=7, baseline_days=baseline_days)
    prior_workload_score = clamp(max(prior_load_score, prior_duration_score, prior_distance_score, prior_fatigue_score, recent_load_score))
    tissue_load_score = clamp(max(prior_impact_score, prior_running_score))
    metabolic_fatigue_score = clamp(max(prior_load_score, prior_fatigue_score, recent_load_score))

    current_duration_low = percentile_score(history["duration"], row["duration"], "low")
    current_distance_low = percentile_score(history["distance"], row["distance"], "low")
    current_load_low = percentile_score(history["load"], row["load"], "low")
    rest_context_score = clamp(0.4 * current_duration_low + 0.4 * current_distance_low + 0.2 * current_load_low)

    if recent_7.empty:
        insufficient_rest_score = 0.0
    else:
        high_load_days = (recent_7["load"].rank(pct=True) > 0.75).sum()
        low_recovery_days = (recent_7["readiness"] < 50).sum()
        easy_days = ((recent_7["duration"] <= recent_7["duration"].median()) & (recent_7["load"] <= recent_7["load"].median())).sum()
        insufficient_rest_score = clamp((high_load_days * 14) + (low_recovery_days * 12) + max(0, 2 - easy_days) * 12)

    delayed_response_score = prior_workload_score * recovery_strain / 100.0
    tissue_mismatch_score = tissue_load_score * recovery_strain / 100.0
    run_under_recovered_score = max(
        percentile_score(history["running_duration"], row["running_duration"], "high"),
        percentile_score(history["running_distance"], row["running_distance"], "high"),
    ) * recovery_strain / 100.0
    standalone_recovery_score = recovery_strain * 0.75
    accumulated_score = insufficient_rest_score * 0.65
    novelty_support = row["state_novelty_score"] * 0.15 if recovery_strain >= 40 else 0.0
    preparedness_mismatch_score = clamp(max(delayed_response_score, tissue_mismatch_score, run_under_recovered_score))
    risk_score = max(preparedness_mismatch_score, standalone_recovery_score, accumulated_score) + novelty_support

    if rest_context_score >= 70 and recovery_strain < 35 and prior_workload_score < 60:
        risk_score *= 0.35

    risk_score = clamp(risk_score)
    if risk_score >= 70:
        risk_level = "high"
    elif risk_score >= 45:
        risk_level = "moderate"
    else:
        risk_level = "low"

    if risk_level == "low" and rest_context_score >= 70 and recovery_strain < 35:
        risk_reason = "low-risk rest/easy day"
    elif risk_level == "low" and row["state_novelty_score"] >= 70 and recovery_strain < 35:
        risk_reason = "novel but not clearly risky"
    elif risk_level == "low":
        risk_reason = "low risk"
    elif run_under_recovered_score >= max(delayed_response_score, tissue_mismatch_score, standalone_recovery_score, accumulated_score) and run_under_recovered_score >= 35:
        risk_reason = "running while under-recovered"
    elif tissue_mismatch_score >= max(delayed_response_score, standalone_recovery_score, accumulated_score) and tissue_mismatch_score >= 35:
        risk_reason = "tissue-load recovery mismatch"
    elif delayed_response_score >= max(standalone_recovery_score, accumulated_score) and delayed_response_score >= 35:
        risk_reason = "post-load recovery response"
    elif accumulated_score >= max(delayed_response_score, standalone_recovery_score) and accumulated_score >= 35:
        risk_reason = "accumulated insufficient rest"
    elif standalone_recovery_score >= 35:
        risk_reason = "poor recovery markers"
    else:
        risk_reason = "low risk"

    run_under_recovered_clamped = clamp(run_under_recovered_score)

    return {
        "date": row["date"].date().isoformat(),
        "split": row.get("split"),
        "risk_score": risk_score,
        "risk_level": risk_level,
        "risk_reason": risk_reason,
        "state_novelty_score": value_or_none(row["state_novelty_score"]),
        "raw_anomaly_zscore": value_or_none(row.get("anomaly_zscore")),
        "recovery_strain_score": recovery_strain,
        "prior_workload_score": prior_workload_score,
        "tissue_load_score": tissue_load_score,
        "metabolic_fatigue_score": metabolic_fatigue_score,
        "preparedness_mismatch_score": preparedness_mismatch_score,
        "run_under_recovered_score": run_under_recovered_clamped,
        "rest_context_score": rest_context_score,
        "insufficient_rest_score": insufficient_rest_score,
        "readiness": value_or_none(row["readiness"]),
        "hrv": value_or_none(row["hrv"]),
        "resting_hr": value_or_none(row["resting_hr"]),
        "load": value_or_none(row["load"]),
        "duration": value_or_none(row["duration"]),
        "distance": value_or_none(row["distance"]),
        "previous_day_load": previous_day_load,
        "previous_day_duration": previous_day_duration,
        "previous_day_distance": previous_day_distance,
        "previous_day_impact_duration": previous_day_impact_duration,
        "previous_day_running_distance": previous_day_running_distance,
        "previous_day_cycling_distance": previous_day_cycling_distance,
        "running_duration": value_or_none(row["running_duration"]),
        "running_distance": value_or_none(row["running_distance"]),
        "cycling_duration": value_or_none(row["cycling_duration"]),
        "cycling_distance": value_or_none(row["cycling_distance"]),
        "impact_duration": value_or_none(row["impact_duration"]),
        "fatigue_duration": value_or_none(row["fatigue_duration"]),
        "readiness_risk": readiness_risk,
        "hrv_risk": hrv_risk,
        "resting_hr_risk": resting_hr_risk,
        "sleep_risk": sleep_risk,
        "body_battery_risk": body_battery_risk,
    }


BONE_STRESS_OUTPUT_COLUMNS = [
    "bone_stress_risk_score",
    "literature_bone_stress_score",
    "personalized_bone_stress_score",
    "literature_bone_stress_level",
    "personalized_bone_stress_level",
    "integrated_bone_stress_score",
    "frontier_strain_score",
    "frontier_strain_level",
    "accumulated_frontier_state",
    "accumulated_frontier_level",
    "embedding_novelty_score",
    "readiness_forecast_error_score",
    "readiness_absolute_forecast_error_score",
    "reference_block_similarity_score",
    "monitoring_signal_agreement",
    "operational_alert_tier",
    "operational_alert_label",
    "counterfactual_hint",
    "operational_recommendation",
    "reference_archetype_id",
    "reference_archetype_label",
    "reference_archetype_score",
    "embedding_neighbor_summary",
    "contrastive_novelty_score",
    "frontier_attribution_summary",
    "frontier_attribution_drivers",
    "whatif_volume_15_summary",
    "whatif_volume_45_summary",
    "whatif_best_scenario_summary",
    "running_acwr_zone",
    "running_edwards_speed_band",
    "foster_monotony",
    "foster_strain",
    "bone_stress_severity_score",
    "bone_stress_risk_level",
    "bone_stress_risk_reason",
    "running_7d_load_score",
    "running_28d_load_score",
    "running_7d_volume_score",
    "running_28d_volume_score",
    "running_intensity_score",
    "running_workout_score",
    "running_acwr_score",
    "running_progression_score",
    "running_monotony_score",
    "run_under_recovered_score",
    "running_7d_sum_m",
    "running_28d_sum_m",
    "running_7d_load_sum",
    "running_28d_load_sum",
    "running_avg_speed",
    "running_max_speed",
    "running_aerobic_te",
    "running_anaerobic_te",
    "daily_bone_stress_contribution",
    "accumulated_bone_stress_state",
    "accumulated_bone_stress_level",
    "bone_stress_carryover_score",
]


def merge_bone_stress_scores(scores: pd.DataFrame, bone_stress: pd.DataFrame) -> pd.DataFrame:
    merged = scores.drop(columns=[col for col in BONE_STRESS_OUTPUT_COLUMNS if col in scores.columns], errors="ignore").copy()
    bone_subset = bone_stress[["date", *BONE_STRESS_OUTPUT_COLUMNS]].copy()
    merge_key = "_merge_date"
    merged[merge_key] = pd.to_datetime(merged["date"])
    bone_subset[merge_key] = pd.to_datetime(bone_subset["date"])
    return merged.merge(bone_subset.drop(columns=["date"]), on=merge_key, how="left").drop(columns=[merge_key])


def score_risk(frame: pd.DataFrame, baseline_days: int) -> pd.DataFrame:
    rows = [score_row(frame, idx, baseline_days) for idx in range(len(frame))]
    return pd.DataFrame(rows)


def daily_strain_contribution(row: pd.Series) -> float:
    """Daily input to accumulated risk: poor recovery markers plus exercise load signals."""
    return clamp(
        0.35 * float(row["recovery_strain_score"])
        + 0.25 * float(row["metabolic_fatigue_score"])
        + 0.20 * float(row["tissue_load_score"])
        + 0.20 * float(row["insufficient_rest_score"])
    )


def compute_accumulated_risk_state(scores: pd.DataFrame, decay: float) -> pd.DataFrame:
    """Carry risk forward day to day so hard blocks build state and easy days let it decay."""
    enriched = scores.copy()
    contributions = enriched.apply(daily_strain_contribution, axis=1)
    carry = 0.0
    states: list[float] = []
    for contribution in contributions:
        carry = decay * carry + (1.0 - decay) * contribution
        states.append(clamp(carry))
    enriched["daily_strain_contribution"] = contributions
    enriched["accumulated_risk_state"] = states
    enriched["accumulated_risk_level"] = enriched["accumulated_risk_state"].map(
        lambda value: "high" if value >= 65 else "moderate" if value >= 45 else "low"
    )
    return enriched


def build_period_summary(block: pd.DataFrame) -> str:
    start = block["date"].min().date().isoformat()
    end = block["date"].max().date().isoformat()
    calendar_days = int((block["date"].max() - block["date"].min()).days + 1)
    peak = float(block["accumulated_risk_state"].max())
    high_days = int((block["risk_level"] == "high").sum())
    dominant_reason = block["risk_reason"].mode().iloc[0] if not block.empty else "unknown"
    min_readiness = block["readiness"].min(skipna=True)
    readiness_text = f" Lowest readiness {min_readiness:.0f}." if pd.notna(min_readiness) else ""
    return (
        f"Sustained elevated risk from {start} to {end} ({calendar_days} calendar days). "
        f"Accumulated state peaked at {peak:.0f} with {high_days} high-risk day(s). "
        f"Dominant pattern: {str(dominant_reason).replace('_', ' ')}.{readiness_text}"
    )


def detect_risk_periods(
    scores: pd.DataFrame,
    threshold: float,
    min_elevated_days: int,
    max_gap_days: int,
) -> pd.DataFrame:
    """Group nearby elevated accumulated-risk days into interpretable periods."""
    frame = scores.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    elevated_indices = frame.index[frame["accumulated_risk_state"] >= threshold].tolist()
    if not elevated_indices:
        return pd.DataFrame()

    groups: list[list[int]] = []
    current = [elevated_indices[0]]
    for index in elevated_indices[1:]:
        gap_days = (frame.loc[index, "date"] - frame.loc[current[-1], "date"]).days
        if gap_days <= max_gap_days + 1:
            current.append(index)
        else:
            groups.append(current)
            current = [index]
    groups.append(current)

    rows: list[dict[str, object]] = []
    for period_id, group in enumerate(groups, start=1):
        if len(group) < min_elevated_days:
            continue
        block = frame.loc[group[0] : group[-1]].copy()
        rows.append(
            {
                "period_id": period_id,
                "start_date": block["date"].min().date().isoformat(),
                "end_date": block["date"].max().date().isoformat(),
                "calendar_days": int((block["date"].max() - block["date"].min()).days + 1),
                "elevated_days": int((block["accumulated_risk_state"] >= threshold).sum()),
                "high_risk_days": int((block["risk_level"] == "high").sum()),
                "peak_accumulated_risk_state": float(block["accumulated_risk_state"].max()),
                "mean_accumulated_risk_state": float(block["accumulated_risk_state"].mean()),
                "mean_recovery_strain": float(block["recovery_strain_score"].mean()),
                "mean_metabolic_fatigue": float(block["metabolic_fatigue_score"].mean()),
                "mean_tissue_load": float(block["tissue_load_score"].mean()),
                "min_readiness": value_or_none(block["readiness"].min(skipna=True)),
                "dominant_risk_reason": block["risk_reason"].mode().iloc[0],
                "period_level": "high" if block["accumulated_risk_state"].max() >= 65 else "moderate",
                "period_summary": build_period_summary(block),
            }
        )
    return pd.DataFrame(rows)


def build_bone_stress_period_summary(block: pd.DataFrame) -> str:
    start = block["date"].min().date().isoformat()
    end = block["date"].max().date().isoformat()
    calendar_days = int((block["date"].max() - block["date"].min()).days + 1)
    peak = float(block["accumulated_bone_stress_state"].max())
    high_days = int((block["bone_stress_risk_level"] == "high").sum())
    dominant_reason = block["bone_stress_risk_reason"].mode().iloc[0] if not block.empty else "unknown"
    run7 = pd.to_numeric(block["running_7d_sum_m"], errors="coerce")
    peak_run7_km = float(run7.max() / 1000.0) if run7.notna().any() else None
    run_text = f" Peak 7-day running total {peak_run7_km:.0f} km." if peak_run7_km is not None else ""
    return (
        f"Sustained elevated bone-stress load from {start} to {end} ({calendar_days} calendar days). "
        f"Accumulated bone-stress state peaked at {peak:.0f} with {high_days} high day(s). "
        f"Dominant pattern: {str(dominant_reason).replace('_', ' ')}.{run_text}"
    )


def detect_bone_stress_periods(
    scores: pd.DataFrame,
    max_gap_days: int,
    min_high_days: int,
    min_peak_state: float,
    max_span_days: int,
) -> pd.DataFrame:
    """Detect running-load blocks by clustering high bone-stress days.

    Slow-decay accumulated state can stay above moderate thresholds for months,
    which produces unrealistically long periods if you merge on state alone.
    Instead, cluster days flagged high and split long spans at the largest gap.
    """
    frame = scores.copy().sort_values("date").reset_index(drop=True)
    frame["date"] = pd.to_datetime(frame["date"])
    high_mask = frame["bone_stress_risk_level"] == "high"
    high_indices = frame.index[high_mask].tolist()
    if not high_indices:
        return pd.DataFrame()

    groups: list[list[int]] = [[high_indices[0]]]
    for index in high_indices[1:]:
        gap_days = (frame.loc[index, "date"] - frame.loc[groups[-1][-1], "date"]).days
        if gap_days <= max_gap_days:
            groups[-1].append(index)
        else:
            groups.append([index])

    def split_group(idxs: list[int]) -> list[list[int]]:
        if len(idxs) < 2:
            return [idxs]
        dates = frame.loc[idxs, "date"]
        span = (dates.max() - dates.min()).days + 1
        if span <= max_span_days:
            return [idxs]
        gaps = [
            (int((frame.loc[idxs[i + 1], "date"] - frame.loc[idxs[i], "date"]).days), i)
            for i in range(len(idxs) - 1)
        ]
        split_at = max(gaps)[1] + 1
        left, right = idxs[:split_at], idxs[split_at:]
        parts: list[list[int]] = []
        if len(left) >= min_high_days:
            parts.extend(split_group(left))
        if len(right) >= min_high_days:
            parts.extend(split_group(right))
        return parts if parts else [idxs]

    final_groups: list[list[int]] = []
    for group in groups:
        if len(group) < min_high_days:
            continue
        final_groups.extend(split_group(group))

    rows: list[dict[str, object]] = []
    for period_id, group in enumerate(final_groups, start=1):
        if len(group) < min_high_days:
            continue
        block = frame.loc[group[0] : group[-1]].copy()
        peak_state = float(block["accumulated_bone_stress_state"].max())
        if peak_state < min_peak_state:
            continue
        run7 = pd.to_numeric(block["running_7d_sum_m"], errors="coerce")
        rows.append(
            {
                "period_id": period_id,
                "start_date": block["date"].min().date().isoformat(),
                "end_date": block["date"].max().date().isoformat(),
                "calendar_days": int((block["date"].max() - block["date"].min()).days + 1),
                "elevated_days": int(len(group)),
                "high_bone_stress_days": int(high_mask.loc[group].sum()),
                "peak_accumulated_bone_stress_state": peak_state,
                "mean_accumulated_bone_stress_state": float(block["accumulated_bone_stress_state"].mean()),
                "peak_running_7d_km": value_or_none(run7.max() / 1000.0 if run7.notna().any() else None),
                "mean_running_7d_km": value_or_none(run7.mean() / 1000.0 if run7.notna().any() else None),
                "mean_running_7d_load_score": float(block["running_7d_load_score"].mean()),
                "mean_running_progression_score": float(block["running_progression_score"].mean()),
                "mean_running_intensity_score": float(block["running_intensity_score"].mean()),
                "dominant_bone_stress_reason": block["bone_stress_risk_reason"].mode().iloc[0],
                "period_level": "high" if peak_state >= 65 else "moderate",
                "period_summary": build_bone_stress_period_summary(block),
            }
        )
    return pd.DataFrame(rows)


def save_risk_plots(scores: pd.DataFrame, output_dir: Path) -> None:
    dates = pd.to_datetime(scores["date"])
    fig, ax1 = plt.subplots(figsize=(13, 5))
    ax1.plot(dates, scores["risk_score"], label="Risk score", color="tab:red")
    ax1.plot(dates, scores["recovery_strain_score"], label="Recovery strain", color="tab:orange", alpha=0.85)
    ax1.set_title("Risk Score And Recovery Strain Over Time")
    ax1.set_xlabel("Date")
    ax1.set_ylabel("Score (0-100)")
    ax1.grid(alpha=0.25)
    ax1.legend(loc="upper left")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / "risk_score_over_time.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 6))
    scatter = ax.scatter(scores["prior_workload_score"], scores["recovery_strain_score"], c=scores["risk_score"], cmap="viridis", s=24, alpha=0.8)
    ax.set_title("Prior Workload vs Next-Day Recovery Strain")
    ax.set_xlabel("Prior workload score (0-100)")
    ax.set_ylabel("Recovery strain score (0-100)")
    ax.grid(alpha=0.25)
    fig.colorbar(scatter, ax=ax, label="Risk score")
    fig.tight_layout()
    fig.savefig(output_dir / "prior_workload_vs_recovery_strain.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(13, 4))
    ax.plot(dates, scores["insufficient_rest_score"], label="Insufficient rest score", color="tab:purple")
    ax.set_title("Longitudinal Insufficient-Rest Signal")
    ax.set_xlabel("Date")
    ax.set_ylabel("Score (0-100)")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper left")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / "insufficient_rest_over_time.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 6))
    scatter = ax.scatter(scores["state_novelty_score"], scores["risk_score"], c=scores["rest_context_score"], cmap="viridis", s=24, alpha=0.8)
    ax.set_title("State Novelty vs Risk")
    ax.set_xlabel("State novelty score (0-100)")
    ax.set_ylabel("Risk score (0-100)")
    ax.grid(alpha=0.25)
    fig.colorbar(scatter, ax=ax, label="Rest/easy context score")
    fig.tight_layout()
    fig.savefig(output_dir / "novelty_vs_risk.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(13, 5))
    dates = pd.to_datetime(scores["date"])
    ax.plot(dates, scores["metabolic_fatigue_score"], label="Metabolic fatigue score", color="tab:blue")
    ax.plot(dates, scores["tissue_load_score"], label="Tissue-load score", color="tab:brown", alpha=0.85)
    ax.plot(dates, scores["preparedness_mismatch_score"], label="Preparedness mismatch", color="tab:red", alpha=0.8)
    ax.set_title("Sport-Specific Risk Components")
    ax.set_xlabel("Date")
    ax.set_ylabel("Score (0-100)")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper left")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / "sport_specific_risk_components.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(13, 5))
    ax.plot(dates, scores["risk_score"], label="Daily risk score", color="tab:red", alpha=0.55)
    ax.plot(dates, scores["accumulated_risk_state"], label="Accumulated risk state", color="tab:purple", linewidth=2.0)
    ax.plot(dates, scores["daily_strain_contribution"], label="Daily strain input", color="tab:gray", alpha=0.45)
    ax.axhline(45, color="tab:orange", linestyle="--", linewidth=1, alpha=0.7, label="Moderate state threshold")
    ax.axhline(65, color="tab:red", linestyle="--", linewidth=1, alpha=0.7, label="High state threshold")
    ax.set_title("Daily Risk vs Accumulated Risk State")
    ax.set_xlabel("Date")
    ax.set_ylabel("Score (0-100)")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper left")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / "accumulated_risk_state_over_time.png", dpi=160)
    plt.close(fig)


def save_bone_stress_plots(scores: pd.DataFrame, output_dir: Path) -> None:
    dates = pd.to_datetime(scores["date"])
    fig, ax = plt.subplots(figsize=(13, 5))
    ax.plot(dates, scores["bone_stress_risk_score"], label="Bone-stress risk score", color="tab:brown", alpha=0.85)
    ax.plot(
        dates,
        scores["accumulated_bone_stress_state"],
        label="Accumulated bone-stress state",
        color="tab:orange",
        linewidth=2.0,
    )
    ax.plot(dates, scores["running_7d_load_score"], label="7-day running load score", color="tab:gray", alpha=0.45)
    ax.plot(dates, scores["running_intensity_score"], label="Running intensity score", color="tab:olive", alpha=0.45)
    ax.axhline(45, color="tab:orange", linestyle="--", linewidth=1, alpha=0.7, label="Moderate threshold")
    ax.axhline(65, color="tab:red", linestyle="--", linewidth=1, alpha=0.7, label="High threshold")
    ax.set_title("Running-Centered Bone-Stress Risk Over Time (Full History)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Score (0-100)")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper left")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / "bone_stress_risk_over_time.png", dpi=160)
    plt.close(fig)


def write_summary(scores: pd.DataFrame, periods: pd.DataFrame, output_path: Path) -> None:
    summary = {
        "rows_scored": int(len(scores)),
        "date_range": {
            "start": scores["date"].min(),
            "end": scores["date"].max(),
        },
        "high_risk_days": int((scores["risk_level"] == "high").sum()),
        "moderate_risk_days": int((scores["risk_level"] == "moderate").sum()),
        "high_accumulated_state_days": int((scores["accumulated_risk_level"] == "high").sum()),
        "moderate_accumulated_state_days": int((scores["accumulated_risk_level"] == "moderate").sum()),
        "risk_period_count": int(len(periods)),
        "top_risk_day": scores.sort_values("risk_score", ascending=False).iloc[0].to_dict(),
        "top_accumulated_state_day": scores.sort_values("accumulated_risk_state", ascending=False).iloc[0].to_dict(),
        "top_risk_period": periods.sort_values("peak_accumulated_risk_state", ascending=False).iloc[0].to_dict()
        if not periods.empty
        else None,
        "high_bone_stress_days": int((scores["bone_stress_risk_level"] == "high").sum())
        if "bone_stress_risk_level" in scores.columns
        else 0,
        "top_bone_stress_day": scores.sort_values("bone_stress_risk_score", ascending=False).iloc[0].to_dict()
        if "bone_stress_risk_score" in scores.columns
        else None,
    }
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def write_bone_stress_summary(bone_periods: pd.DataFrame, output_path: Path) -> None:
    summary = {
        "bone_stress_period_count": int(len(bone_periods)),
        "top_bone_stress_period": bone_periods.sort_values(
            "peak_accumulated_bone_stress_state", ascending=False
        ).iloc[0].to_dict()
        if not bone_periods.empty
        else None,
    }
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Score recovery/training risk separately from embedding novelty.")
    parser.add_argument("--embeddings", type=Path, default=Path("outputs/modeling/pretrained_embeddings.csv"))
    parser.add_argument(
        "--contrastive-embeddings",
        type=Path,
        default=Path("outputs/modeling/contrastive_embeddings.csv"),
        help="Optional contrastive encoder embeddings for frontier novelty blend.",
    )
    parser.add_argument(
        "--model-config",
        type=Path,
        default=Path("config/model_features.json"),
        help="Model config for frontier input attribution.",
    )
    parser.add_argument(
        "--pretrained-checkpoint",
        type=Path,
        default=Path("outputs/modeling/masked_tcn/masked_tcn_pretrained.pt"),
        help="Masked TCN checkpoint for frontier input attribution.",
    )
    parser.add_argument("--daily-features", type=Path, default=Path("data/processed/daily_features_with_fit_deduped.csv"))
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw"),
        help="Garmin export root; summarizedActivities JSON is used to correct inflated FIT duplicate running volume.",
    )
    parser.add_argument(
        "--predictions",
        type=Path,
        default=Path("outputs/modeling/masked_tcn_finetuned/finetuned_predictions.csv"),
        help="Fine-tuned readiness predictions for forecast-error frontier signal.",
    )
    parser.add_argument(
        "--outcome-events",
        type=Path,
        default=Path("config/outcome_events.json"),
        help="Labeled reference blocks for embedding similarity (validation only).",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/analysis"))
    parser.add_argument("--baseline-days", type=int, default=28)
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument(
        "--accumulation-decay",
        type=float,
        default=0.86,
        help="Daily decay for accumulated risk state (higher keeps load/recovery context longer).",
    )
    parser.add_argument(
        "--period-threshold",
        type=float,
        default=50.0,
        help="Accumulated risk state threshold for entering a risk period.",
    )
    parser.add_argument(
        "--bone-stress-decay",
        type=float,
        default=0.91,
        help="Daily decay for accumulated bone-stress state (slower than general risk; tissue load clears more slowly).",
    )
    parser.add_argument("--period-min-days", type=int, default=3, help="Minimum elevated days to form a period.")
    parser.add_argument("--period-max-gap-days", type=int, default=1, help="Allow this many calendar gap days inside a period.")
    parser.add_argument(
        "--bone-stress-period-max-gap",
        type=int,
        default=4,
        help="Max calendar gap between high bone-stress days inside one period.",
    )
    parser.add_argument(
        "--bone-stress-period-min-high-days",
        type=int,
        default=5,
        help="Minimum high bone-stress days required to form a period.",
    )
    parser.add_argument(
        "--bone-stress-period-min-peak-state",
        type=float,
        default=60.0,
        help="Minimum peak accumulated bone-stress state within a period.",
    )
    parser.add_argument(
        "--bone-stress-period-max-span",
        type=int,
        default=49,
        help="Split periods longer than this many calendar days at the largest high-day gap.",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    daily_frame = load_daily_frame(args.daily_features, raw_dir=args.raw_dir)
    bone_stress_full = score_bone_stress_history(
        daily_frame,
        baseline_days=args.baseline_days,
        bone_stress_decay=args.bone_stress_decay,
    )
    embeddings = pd.read_csv(args.embeddings, parse_dates=["date"])
    contrastive_embeddings = (
        pd.read_csv(args.contrastive_embeddings, parse_dates=["date"])
        if args.contrastive_embeddings.exists()
        else None
    )
    predictions = pd.read_csv(args.predictions, parse_dates=["date"]) if args.predictions.exists() else None
    bone_stress_full = enrich_frontier_monitoring(
        bone_stress_full,
        embeddings,
        predictions=predictions,
        outcome_events_path=args.outcome_events,
        contrastive_embeddings=contrastive_embeddings,
    )
    bone_stress_full["monitoring_signal_agreement"] = bone_stress_full.apply(
        lambda row: monitoring_agreement(
            str(row.get("literature_bone_stress_level", "low")),
            str(row.get("personalized_bone_stress_level", "low")),
            row.get("accumulated_frontier_level"),
        ),
        axis=1,
    )
    bone_periods = detect_bone_stress_periods(
        bone_stress_full,
        max_gap_days=args.bone_stress_period_max_gap,
        min_high_days=args.bone_stress_period_min_high_days,
        min_peak_state=args.bone_stress_period_min_peak_state,
        max_span_days=args.bone_stress_period_max_span,
    )
    bone_stress_full = enrich_embedding_explanations(
        bone_stress_full,
        embeddings,
        args.outcome_events,
        bone_periods=bone_periods,
    )
    bone_stress_full["operational_alert_tier"] = bone_stress_full.apply(operational_alert_tier, axis=1)
    bone_stress_full["operational_alert_label"] = bone_stress_full["operational_alert_tier"].map(tier_label)
    bone_stress_full["counterfactual_hint"] = bone_stress_full.apply(counterfactual_hint, axis=1)
    bone_stress_full["operational_recommendation"] = bone_stress_full.apply(tier_recommendation, axis=1)
    bone_stress_full = enrich_counterfactual_scenarios(bone_stress_full)
    if args.pretrained_checkpoint.exists():
        bone_stress_full = enrich_frontier_attribution(
            bone_stress_full,
            args.model_config,
            args.pretrained_checkpoint,
        )
    bone_stress_full.to_csv(args.output_dir / "athlete_bone_stress_scores.csv", index=False)
    top_bone_stress = bone_stress_full.sort_values(
        ["bone_stress_severity_score", "running_7d_load_score", "bone_stress_risk_score"],
        ascending=False,
    ).head(args.top_n)
    top_bone_stress.to_csv(args.output_dir / "top_bone_stress_days.csv", index=False)
    bone_periods.to_csv(args.output_dir / "athlete_bone_stress_periods.csv", index=False)
    top_bone_periods = bone_periods.sort_values(
        ["peak_accumulated_bone_stress_state", "calendar_days"],
        ascending=False,
    ).head(args.top_n)
    top_bone_periods.to_csv(args.output_dir / "top_bone_stress_periods.csv", index=False)
    write_bone_stress_summary(bone_periods, args.output_dir / "athlete_bone_stress_summary.json")

    frame = load_inputs(args.embeddings, args.daily_features, raw_dir=args.raw_dir)
    scores = score_risk(frame, baseline_days=args.baseline_days)
    scores = compute_accumulated_risk_state(scores, decay=args.accumulation_decay)
    scores = merge_bone_stress_scores(scores, bone_stress_full)
    periods = detect_risk_periods(
        scores,
        threshold=args.period_threshold,
        min_elevated_days=args.period_min_days,
        max_gap_days=args.period_max_gap_days,
    )
    scores.to_csv(args.output_dir / "athlete_risk_scores.csv", index=False)
    top_risk = scores.sort_values(["risk_score", "recovery_strain_score"], ascending=False).head(args.top_n)
    top_risk.to_csv(args.output_dir / "top_risk_days.csv", index=False)
    top_periods = periods.sort_values(["peak_accumulated_risk_state", "calendar_days"], ascending=False).head(args.top_n)
    top_periods.to_csv(args.output_dir / "top_risk_periods.csv", index=False)
    periods.to_csv(args.output_dir / "athlete_risk_periods.csv", index=False)
    save_risk_plots(scores, args.output_dir)
    save_bone_stress_plots(bone_stress_full, args.output_dir)
    write_summary(scores, periods, args.output_dir / "athlete_risk_summary.json")
    print(
        f"Wrote athlete risk outputs to {args.output_dir} "
        f"(bone-stress history: {len(bone_stress_full)} days, {bone_stress_full['date'].min()} to {bone_stress_full['date'].max()})"
    )


if __name__ == "__main__":
    main()
