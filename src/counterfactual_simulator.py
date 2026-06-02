"""Deterministic what-if scenarios for running volume reductions."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.bone_stress_literature import (
    absolute_acwr_risk,
    absolute_running_volume_risk,
    foster_monotony_strain,
    literature_bone_stress_score,
)


def _scale_running_window(frame: pd.DataFrame, idx: int, factor: float, lookback_days: int = 7) -> pd.DataFrame:
    modified = frame.copy()
    end_date = modified.iloc[idx]["date"]
    start_date = end_date - pd.Timedelta(days=lookback_days - 1)
    mask = (modified["date"] >= start_date) & (modified["date"] <= end_date)
    for column in ("running_distance", "running_duration", "running_7d_load_sum"):
        if column not in modified.columns:
            continue
        if column == "running_7d_load_sum":
            modified.loc[mask, column] = pd.to_numeric(modified.loc[mask, column], errors="coerce") * factor
            continue
        values = pd.to_numeric(modified.loc[mask, column], errors="coerce")
        modified.loc[mask, column] = values * factor
    modified.loc[mask, "running_7d_sum_m"] = pd.to_numeric(modified.loc[mask, "running_7d_sum_m"], errors="coerce") * factor
    if "running_28d_sum_m" in modified.columns:
        modified.loc[mask, "running_28d_sum_m"] = pd.to_numeric(modified.loc[mask, "running_28d_sum_m"], errors="coerce") * factor
    if "running_7d_acwr" in modified.columns and "running_28d_load_sum" in modified.columns:
        modified.loc[mask, "running_7d_load_sum"] = pd.to_numeric(modified.loc[mask, "running_7d_load_sum"], errors="coerce") * factor
        load7 = pd.to_numeric(modified.loc[mask, "running_7d_load_sum"], errors="coerce")
        load28 = pd.to_numeric(modified.loc[mask, "running_28d_load_sum"], errors="coerce")
        modified.loc[mask, "running_7d_acwr"] = np.where(load28 > 0, 4.0 * load7 / load28, np.nan)
    return modified


def estimate_scores_for_row(row: pd.Series, week_loads: pd.Series | None = None) -> dict[str, float]:
    run7_km = float(pd.to_numeric(row.get("running_7d_sum_m"), errors="coerce") or 0) / 1000.0
    if week_loads is None:
        week_loads = pd.Series([row.get("running_7d_load_sum", row.get("running_distance", 0))])
    foster_monotony, foster_strain = foster_monotony_strain(week_loads)
    session_speed = pd.to_numeric(row.get("running_avg_speed"), errors="coerce")
    literature = literature_bone_stress_score(
        row.get("running_7d_acwr"),
        session_speed,
        run7_km,
        foster_monotony,
        foster_strain,
    )
    return {
        "literature_score": float(literature),
        "absolute_volume_score": float(absolute_running_volume_risk(run7_km)),
        "absolute_acwr_score": float(absolute_acwr_risk(row.get("running_7d_acwr"))),
        "run7_km": run7_km,
    }


def simulate_volume_reduction(
    frame: pd.DataFrame,
    idx: int,
    factor: float,
    lookback_days: int = 7,
) -> dict[str, float | str]:
    baseline_row = frame.iloc[idx]
    week_start = baseline_row["date"] - pd.Timedelta(days=6)
    load_column = "running_7d_load_sum" if "running_7d_load_sum" in frame.columns else "running_distance"
    week_loads = frame.loc[(frame["date"] >= week_start) & (frame["date"] <= baseline_row["date"]), load_column]
    baseline = estimate_scores_for_row(baseline_row, week_loads=week_loads)
    modified = _scale_running_window(frame, idx, factor, lookback_days=lookback_days)
    scenario_row = modified.iloc[idx]
    scenario_week = modified.loc[
        (modified["date"] >= week_start) & (modified["date"] <= scenario_row["date"]),
        load_column,
    ]
    scenario = estimate_scores_for_row(scenario_row, week_loads=scenario_week)
    delta = float(scenario["literature_score"] - baseline["literature_score"])
    pct = int(round((1.0 - factor) * 100))
    summary = (
        f"If 7-day running volume were ~{pct}% lower ({scenario['run7_km']:.0f} vs {baseline['run7_km']:.0f} km/week), "
        f"literature score would move {baseline['literature_score']:.0f} → {scenario['literature_score']:.0f} "
        f"({delta:+.0f})."
    )
    return {
        "factor": factor,
        "baseline_literature_score": baseline["literature_score"],
        "scenario_literature_score": scenario["literature_score"],
        "baseline_run7_km": baseline["run7_km"],
        "scenario_run7_km": scenario["run7_km"],
        "delta_literature_score": delta,
        "summary": summary,
    }


def enrich_counterfactual_scenarios(
    scores: pd.DataFrame,
    factors: tuple[float, ...] = (0.85, 0.55),
) -> pd.DataFrame:
    """Attach what-if summaries for the latest scored day."""
    enriched = scores.copy()
    enriched["whatif_volume_15_summary"] = None
    enriched["whatif_volume_45_summary"] = None
    enriched["whatif_best_scenario_summary"] = None

    enriched["date"] = pd.to_datetime(enriched["date"])
    if enriched.empty:
        return enriched

    frame = enriched.sort_values("date").reset_index(drop=True)
    idx = len(frame) - 1
    scenarios = [simulate_volume_reduction(frame, idx, factor) for factor in factors]
    mask = enriched["date"] == frame.iloc[idx]["date"]
    if len(scenarios) >= 1:
        enriched.loc[mask, "whatif_volume_15_summary"] = scenarios[0]["summary"]
    if len(scenarios) >= 2:
        enriched.loc[mask, "whatif_volume_45_summary"] = scenarios[1]["summary"]
    best = min(scenarios, key=lambda item: item["scenario_literature_score"])
    enriched.loc[mask, "whatif_best_scenario_summary"] = best["summary"]
    return enriched
