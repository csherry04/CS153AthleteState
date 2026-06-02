"""Literature-anchored bone-stress monitoring primitives.

References (see SCIENTIFIC_RATIONALE.md):
- Gabbett (2016): ACWR sweet spot 0.8–1.3, danger zone >= 1.5 [45]
- Napier et al. (2021): volume progression, duration-before-intensity [8]
- Edwards et al. (2010): speed/magnitude bands at 2.5, 3.5, 4.5 m/s [9]
- Foster (1998): monotony = mean/SD; strain = load × monotony [5]
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

# Gabbett / Napier ACWR zones
ACWR_UNDERTRAINING = 0.8
ACWR_SWEET_SPOT_HIGH = 1.3
ACWR_DANGER_ZONE = 1.5

# Edwards et al. (2010) model speeds (m/s)
EDWARDS_SPEED_LOW = 2.5
EDWARDS_SPEED_MODERATE = 3.5
EDWARDS_SPEED_HIGH = 4.5

# Foster monotony (historical monitoring threshold)
FOSTER_MONOTONY_ELEVATED = 2.0
FOSTER_MONOTONY_HIGH = 2.5
FOSTER_MONOTONY_CAP = 10.0


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return float(max(low, min(high, value)))


def absolute_acwr_risk(acwr: object) -> float:
    """Map ACWR to 0–100 using Gabbett-style zones [1,2,8,45]."""
    if pd.isna(acwr):
        return 0.0
    value = float(acwr)
    if value < ACWR_UNDERTRAINING:
        return 25.0
    if value <= 1.0:
        return 20.0
    if value <= ACWR_SWEET_SPOT_HIGH:
        return 35.0
    if value <= ACWR_DANGER_ZONE:
        return 65.0
    if value <= 1.8:
        return 85.0
    return 100.0


def acwr_zone_label(acwr: object) -> str:
    if pd.isna(acwr):
        return "unknown"
    value = float(acwr)
    if value < ACWR_UNDERTRAINING:
        return "undertraining"
    if value <= ACWR_SWEET_SPOT_HIGH:
        return "sweet_spot"
    if value <= ACWR_DANGER_ZONE:
        return "elevated_progression"
    return "danger_zone"


def absolute_edwards_speed_risk(speed_mps: object) -> float:
    """Edwards probabilistic model speeds: magnitude risk rises above ~3.5 m/s [9]."""
    if pd.isna(speed_mps):
        return 0.0
    speed = float(speed_mps)
    if speed <= EDWARDS_SPEED_LOW:
        return 15.0
    if speed <= EDWARDS_SPEED_MODERATE:
        return 40.0
    if speed <= EDWARDS_SPEED_HIGH:
        return 75.0
    return 95.0


def edwards_speed_band(speed_mps: object) -> str:
    if pd.isna(speed_mps) or float(speed_mps) <= 0:
        return "none"
    speed = float(speed_mps)
    if speed <= EDWARDS_SPEED_LOW:
        return "low_magnitude"
    if speed <= EDWARDS_SPEED_MODERATE:
        return "moderate"
    if speed <= EDWARDS_SPEED_HIGH:
        return "elevated"
    return "high_magnitude"


def absolute_running_volume_risk(km_7d: object) -> float:
    """Loading-cycle exposure tiers; individualized history still matters [8]."""
    if pd.isna(km_7d):
        return 0.0
    km = float(km_7d)
    if km <= 15:
        return 10.0
    if km <= 30:
        return 25.0
    if km <= 50:
        return 40.0
    if km <= 70:
        return 55.0
    if km <= 90:
        return 70.0
    if km <= 110:
        return 82.0
    if km <= 130:
        return 92.0
    return 100.0


def foster_monotony_strain(daily_loads: pd.Series) -> tuple[float, float]:
    """Foster monotony and strain from daily session loads [5]."""
    values = pd.to_numeric(daily_loads, errors="coerce").fillna(0.0)
    if values.sum() <= 0:
        return 0.0, 0.0
    mean = float(values.mean())
    std = float(values.std(ddof=0))
    if std <= 0:
        monotony = FOSTER_MONOTONY_CAP
    else:
        monotony = min(mean / std, FOSTER_MONOTONY_CAP)
    weekly_load = float(values.sum())
    strain = weekly_load * monotony
    return monotony, strain


def foster_monotony_risk(monotony: float) -> float:
    if monotony <= 0:
        return 0.0
    if monotony < 1.5:
        return 20.0
    if monotony < FOSTER_MONOTONY_ELEVATED:
        return 40.0
    if monotony < FOSTER_MONOTONY_HIGH:
        return 65.0
    return 85.0


def foster_strain_risk(strain: float, reference_strain: float = 250_000.0) -> float:
    if strain <= 0:
        return 0.0
    return clamp(100.0 * (1.0 - math.exp(-strain / reference_strain)))


def is_edwards_hard_running_session(speed_mps: object, daily_km: float) -> bool:
    """Hard session when speed enters Edwards elevated band with meaningful distance [8,9]."""
    if pd.isna(speed_mps) or daily_km < 5.0:
        return False
    return float(speed_mps) >= EDWARDS_SPEED_MODERATE


def literature_bone_stress_score(
    acwr: object,
    speed_mps: object,
    km_7d: float,
    foster_monotony: float,
    foster_strain: float,
) -> float:
    """Objective literature composite without individualized percentiles."""
    volume_risk = absolute_running_volume_risk(km_7d)
    progression_risk = clamp(0.65 * absolute_acwr_risk(acwr) + 0.35 * volume_risk)
    magnitude_risk = absolute_edwards_speed_risk(speed_mps)
    monotony_risk = foster_monotony_risk(foster_monotony) * (0.35 + 0.65 * volume_risk / 100.0)
    strain_risk = foster_strain_risk(foster_strain) * (0.35 + 0.65 * volume_risk / 100.0)

    blended = clamp(
        0.28 * volume_risk
        + 0.27 * progression_risk
        + 0.20 * magnitude_risk
        + 0.15 * monotony_risk
        + 0.10 * strain_risk
    )
    spike = max(
        progression_risk * 0.92 if acwr_zone_label(acwr) in {"elevated_progression", "danger_zone"} else 0.0,
        monotony_risk * 0.85 if foster_monotony >= FOSTER_MONOTONY_ELEVATED else 0.0,
        magnitude_risk * 0.80 if is_edwards_hard_running_session(speed_mps, km_7d / 7.0) else 0.0,
    )
    return clamp(max(blended, spike))


def risk_level(score: float) -> str:
    if score >= 70:
        return "high"
    if score >= 45:
        return "moderate"
    return "low"


def monitoring_agreement(literature_level: str, personalized_level: str, frontier_level: str | None) -> str:
    if frontier_level in (None, "", "None") or (isinstance(frontier_level, float) and pd.isna(frontier_level)):
        return "literature_personalized_agree" if literature_level == personalized_level else "mixed_signals"

    if literature_level == personalized_level == frontier_level:
        return "all_agree"
    if literature_level == personalized_level:
        return "literature_personalized_agree_frontier_differs"
    if frontier_level == literature_level:
        return "literature_frontier_agree"
    if frontier_level == personalized_level:
        return "personalized_frontier_agree"
    return "mixed_signals"
