"""Input attribution for frontier disagreement days."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import torch

from src.modeling.dataset import load_config
from src.modeling.inference import build_all_inference_windows
from src.modeling.tcn import TCNMaskedAutoencoder


FEATURE_LABELS: dict[str, str] = {
    "running_distance_m": "Running distance",
    "running_duration_seconds": "Running duration",
    "running_avg_hr": "Running heart rate",
    "running_max_hr": "Running max HR",
    "cycling_distance_m": "Cycling distance",
    "cycling_duration_seconds": "Cycling duration",
    "load_dailyTrainingLoadAcute": "Acute training load",
    "load_dailyAcuteChronicWorkloadRatio": "ACWR",
    "readiness_score": "Readiness",
    "readiness_hrvWeeklyAverage": "HRV",
    "wellness_restingHeartRate": "Resting HR",
    "sleep_total_seconds": "Sleep duration",
    "wellness_bodyBattery_chargedValue": "Body battery charged",
    "wellness_bodyBattery_drainedValue": "Body battery drained",
    "activity_training_load": "Activity training load",
    "impact_weighted_duration_seconds": "Impact duration",
    "fatigue_weighted_duration_seconds": "Fatigue duration",
}


def label_feature(name: str) -> str:
    return FEATURE_LABELS.get(name, name.replace("_", " "))


def flagged_for_attribution(row: pd.Series) -> bool:
    tier = str(row.get("operational_alert_tier", "clear"))
    agreement = str(row.get("monitoring_signal_agreement", ""))
    if tier in {"investigate_state", "adjust_training"}:
        return True
    if agreement in {"literature_personalized_agree_frontier_differs", "mixed_signals", "all_agree"}:
        return True
    if row.get("frontier_strain_level") == "high" and row.get("literature_bone_stress_level") != "high":
        return True
    return False


def compute_input_attribution(
    model: torch.nn.Module,
    window: np.ndarray,
    feature_names: list[str],
    device: torch.device,
) -> list[tuple[str, float]]:
    tensor = torch.from_numpy(window).float().unsqueeze(0).to(device)
    tensor.requires_grad_(True)
    model.zero_grad(set_to_none=True)
    _, embedding = model.encoder(tensor)
    target = embedding.norm(dim=1).sum()
    target.backward()
    if tensor.grad is None:
        return []
    grads = tensor.grad.detach().abs().sum(dim=1).squeeze(0).cpu().numpy()
    ranked = sorted(
        ((feature_names[idx], float(grads[idx])) for idx in range(min(len(feature_names), len(grads)))),
        key=lambda item: item[1],
        reverse=True,
    )
    return ranked[:8]


def attribution_summary(ranked: list[tuple[str, float]]) -> tuple[str, str]:
    if not ranked:
        return "", ""
    top = ranked[:5]
    labels = [label_feature(name) for name, _ in top]
    summary = "Top latent-state drivers: " + ", ".join(labels) + "."
    drivers = "; ".join(f"{label_feature(name)} ({value:.3f})" for name, value in top)
    return summary, drivers


def enrich_frontier_attribution(
    scores: pd.DataFrame,
    config_path: Path,
    pretrained_checkpoint: Path,
    recent_days: int = 90,
) -> pd.DataFrame:
    """Add attribution columns for recent flagged days."""
    enriched = scores.copy()
    enriched["date"] = pd.to_datetime(enriched["date"])
    enriched["frontier_attribution_summary"] = None
    enriched["frontier_attribution_drivers"] = None

    if enriched.empty:
        return enriched

    cutoff = enriched["date"].max() - pd.Timedelta(days=recent_days)
    candidate_mask = enriched["date"] >= cutoff
    flagged_dates = enriched.loc[candidate_mask & enriched.apply(flagged_for_attribution, axis=1), "date"]
    if flagged_dates.empty:
        return enriched

    config = load_config(config_path)
    X, _, dates, _, feature_names = build_all_inference_windows(config)
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    tcn_config = config.get("tcn", {})
    model = TCNMaskedAutoencoder(
        input_channels=len(feature_names),
        hidden_channels=int(tcn_config.get("hidden_channels", 32)),
        embedding_dim=int(tcn_config.get("embedding_dim", 16)),
        kernel_size=int(tcn_config.get("kernel_size", 3)),
        dilations=tcn_config.get("dilations", [1, 2, 4]),
        dropout=float(tcn_config.get("dropout", 0.15)),
    ).to(device)
    checkpoint = torch.load(pretrained_checkpoint, map_location=device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    date_to_index = {pd.Timestamp(day).normalize(): idx for idx, day in enumerate(pd.to_datetime(dates))}
    for target_date in flagged_dates:
        idx = date_to_index.get(pd.Timestamp(target_date).normalize())
        if idx is None:
            continue
        ranked = compute_input_attribution(model, X[idx], feature_names, device)
        summary, drivers = attribution_summary(ranked)
        mask = enriched["date"] == target_date
        enriched.loc[mask, "frontier_attribution_summary"] = summary or None
        enriched.loc[mask, "frontier_attribution_drivers"] = drivers or None

    return enriched
