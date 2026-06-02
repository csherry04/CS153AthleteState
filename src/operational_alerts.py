"""Operational alert tiers and plain-language guidance from monitoring tracks."""

from __future__ import annotations

import pandas as pd


def operational_alert_tier(row: pd.Series) -> str:
    """Map track levels and agreement to an operational tier."""
    lit = str(row.get("literature_bone_stress_level", "low"))
    pers = str(row.get("personalized_bone_stress_level", "low"))
    frontier = row.get("frontier_strain_level")
    agreement = str(row.get("monitoring_signal_agreement", ""))

    if agreement == "all_agree" and "high" in {lit, pers, str(frontier)}:
        return "adjust_training"
    if lit == "high" and pers == "high":
        return "adjust_training"
    if agreement == "mixed_signals" and (pers == "high" or frontier == "high"):
        return "adjust_training"
    if frontier == "high" and lit != "high":
        return "investigate_state"
    if pers == "high" or lit == "high" or frontier == "high":
        return "watch"
    if pers == "moderate" or lit == "moderate" or frontier == "moderate":
        return "watch"
    return "clear"


def tier_label(tier: str) -> str:
    return {
        "adjust_training": "Adjust training",
        "investigate_state": "Investigate state",
        "watch": "Watch",
        "clear": "Clear",
    }.get(tier, tier)


def counterfactual_hint(row: pd.Series) -> str:
    """Heuristic guidance on what would likely lower the alert."""
    reason = str(row.get("bone_stress_risk_reason", ""))
    run7_km = float(row.get("running_7d_sum_m") or 0) / 1000.0
    if "progression" in reason:
        target = max(run7_km * 0.85, 0)
        return (
            f"A ~15% reduction in 7-day running volume (from {run7_km:.0f} km toward {target:.0f} km) "
            "would likely lower progression pressure."
        )
    if "volume" in reason or "sustained" in reason:
        return (
            f"Sustained volume is the driver (~{run7_km:.0f} km/week). "
            "A recovery week at 50–60% of recent weekly km would reduce accumulated load."
        )
    if "hard running session" in reason:
        return "Replace the next hard run with easy volume or cross-training; intensity is contributing more than distance."
    if row.get("frontier_strain_level") == "high" and row.get("literature_bone_stress_level") != "high":
        return "Learned state is elevated without extreme load — prioritize sleep, HRV, and readiness before adding intensity."
    if run7_km > 0:
        return f"Moderate 7-day running ({run7_km:.0f} km); avoid stacking hard sessions this week."
    return "Keep progression gradual over the next 7 days."


def tier_recommendation(row: pd.Series) -> str:
    tier = operational_alert_tier(row)
    reason = str(row.get("bone_stress_risk_reason", "elevated context"))
    if tier == "adjust_training":
        return (
            f"Reduce running volume or intensity this week. Dominant pattern: {reason.replace('_', ' ')}. "
            f"{counterfactual_hint(row)}"
        )
    if tier == "investigate_state":
        return (
            "Multivariate strain is elevated while objective load rules are modest. "
            "Check readiness, sleep, and mixed-sport fatigue before progressing. "
            f"{counterfactual_hint(row)}"
        )
    if tier == "watch":
        return f"Monitor closely — {reason.replace('_', ' ')}. {counterfactual_hint(row)}"
    return "No elevated running-load action needed today."
