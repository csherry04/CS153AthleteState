"""Learned-state monitoring signals from TCN embeddings and readiness forecasts."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return float(max(low, min(high, value)))


def embedding_columns(frame: pd.DataFrame, prefix: str = "z_") -> list[str]:
    return [column for column in frame.columns if column.startswith(prefix)]


def contrastive_embedding_columns(frame: pd.DataFrame) -> list[str]:
    return embedding_columns(frame, prefix="cz_")


def normalize_series(values: pd.Series, upper_quantile: float = 0.95, non_negative: bool = True) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    if non_negative:
        numeric = numeric.clip(lower=0.0)
    numeric = numeric.fillna(0.0)
    scale = numeric.quantile(upper_quantile)
    if scale <= 0:
        return numeric * 0.0
    return (numeric / scale).clip(0.0, 1.0) * 100.0


def weighted_frontier_score(
    novelty: pd.Series,
    forecast: pd.Series,
    similarity: pd.Series,
    weights: tuple[float, float, float] = (0.40, 0.35, 0.25),
) -> pd.Series:
    """Blend available frontier components, renormalizing weights when some are missing."""
    weight_array = np.array(weights, dtype=float)
    values = np.column_stack(
        [
            pd.to_numeric(novelty, errors="coerce").to_numpy(dtype=float),
            pd.to_numeric(forecast, errors="coerce").to_numpy(dtype=float),
            pd.to_numeric(similarity, errors="coerce").to_numpy(dtype=float),
        ]
    )
    scores = np.full(len(values), np.nan, dtype=float)
    for idx, row in enumerate(values):
        present = ~np.isnan(row)
        if not present.any():
            continue
        active_weights = weight_array[present]
        active_values = row[present]
        scores[idx] = float(np.clip(np.dot(active_weights, active_values) / active_weights.sum(), 0.0, 100.0))
    return pd.Series(scores, index=novelty.index)


def accumulated_frontier_state(frame: pd.DataFrame) -> pd.Series:
    """Carry frontier strain forward with recovery/load-sensitive decay.

    Daily frontier strain is an acute learned-state signal. This state converts it into
    a slower monitoring signal: it jumps quickly when frontier strain spikes and
    drops only when subsequent days are easy enough to justify decay.
    """
    frontier = pd.to_numeric(frame["frontier_strain_score"], errors="coerce")
    run7_km = pd.to_numeric(frame.get("running_7d_sum_m"), errors="coerce").fillna(0.0) / 1000.0
    recovery = pd.to_numeric(frame.get("recovery_strain_score"), errors="coerce").fillna(0.0)
    accumulated_load = pd.to_numeric(frame.get("accumulated_bone_stress_state"), errors="coerce").fillna(0.0)

    state = np.full(len(frame), np.nan, dtype=float)
    previous = 0.0
    for idx, value in enumerate(frontier):
        if np.isnan(value):
            state[idx] = np.nan
            continue

        if value > previous:
            rise_rate = 0.70
            previous = clamp(previous + rise_rate * (value - previous))
        else:
            if run7_km.iloc[idx] >= 80 or recovery.iloc[idx] >= 55 or accumulated_load.iloc[idx] >= 70:
                decay = 0.97
            elif run7_km.iloc[idx] <= 35 and recovery.iloc[idx] <= 35 and accumulated_load.iloc[idx] <= 45:
                decay = 0.88
            elif run7_km.iloc[idx] <= 50 and recovery.iloc[idx] <= 45 and accumulated_load.iloc[idx] <= 55:
                decay = 0.91
            else:
                decay = 0.94
            previous = clamp(max(value, previous * decay))
        state[idx] = previous

    return pd.Series(state, index=frame.index)


def load_reference_embedding(
    embeddings: pd.DataFrame,
    outcome_events_path: Path,
    event_id: str = "spring_2024_bone_stress",
) -> np.ndarray | None:
    """Mean latent state during a labeled reference load block."""
    payload = json.loads(outcome_events_path.read_text(encoding="utf-8"))
    event = next((item for item in payload.get("events", []) if item.get("id") == event_id), None)
    if event is None:
        return None
    start = pd.Timestamp(event.get("symptom_window_start") or event.get("onset_date"))
    end = pd.Timestamp(event.get("onset_date")) + pd.Timedelta(days=28)
    z_cols = embedding_columns(embeddings)
    if not z_cols:
        return None
    window = embeddings[(embeddings["date"] >= start) & (embeddings["date"] <= end)]
    if window.empty:
        return None
    return window[z_cols].to_numpy(dtype=float).mean(axis=0)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom <= 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def enrich_frontier_monitoring(
    scores: pd.DataFrame,
    embeddings: pd.DataFrame,
    predictions: pd.DataFrame | None = None,
    outcome_events_path: Path | None = None,
    contrastive_embeddings: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Add learned-state monitoring columns where embedding coverage exists."""
    enriched = scores.copy()
    enriched["date"] = pd.to_datetime(enriched["date"])
    emb = embeddings.copy()
    emb["date"] = pd.to_datetime(emb["date"])
    z_cols = embedding_columns(emb)
    merge_cols = ["date", "anomaly_zscore", "embedding_distance", *z_cols]
    merged = enriched.merge(emb[merge_cols], on="date", how="left")

    if contrastive_embeddings is not None and not contrastive_embeddings.empty:
        contrastive = contrastive_embeddings.copy()
        contrastive["date"] = pd.to_datetime(contrastive["date"])
        cz_cols = contrastive_embedding_columns(contrastive)
        contrastive_cols = ["date", "contrastive_anomaly_zscore", *cz_cols]
        contrastive_cols = [column for column in contrastive_cols if column in contrastive.columns]
        merged = merged.merge(contrastive[contrastive_cols], on="date", how="left")
        if "contrastive_anomaly_zscore" in merged.columns:
            positive_contrastive = pd.to_numeric(merged["contrastive_anomaly_zscore"], errors="coerce").clip(lower=0.0)
            merged["contrastive_novelty_score"] = np.where(
                merged["contrastive_anomaly_zscore"].notna(),
                normalize_series(positive_contrastive),
                np.nan,
            )
        else:
            merged["contrastive_novelty_score"] = np.nan
    else:
        merged["contrastive_novelty_score"] = np.nan

    positive_anomaly = pd.to_numeric(merged["anomaly_zscore"], errors="coerce").clip(lower=0.0)
    base_novelty = np.where(
        merged["anomaly_zscore"].notna(),
        normalize_series(positive_anomaly),
        np.nan,
    )
    contrastive_novelty = pd.to_numeric(merged["contrastive_novelty_score"], errors="coerce")
    merged["embedding_novelty_score"] = np.where(
        contrastive_novelty.notna() & pd.notna(base_novelty),
        (0.55 * base_novelty + 0.45 * contrastive_novelty),
        np.where(contrastive_novelty.notna(), contrastive_novelty, base_novelty),
    )

    if predictions is not None and not predictions.empty:
        pred = predictions.copy()
        pred["date"] = pd.to_datetime(pred["date"])
        pred = pred.sort_values("date").drop_duplicates("date", keep="last")
        merged = merged.merge(pred[["date", "actual", "prediction"]], on="date", how="left")
        actual = pd.to_numeric(merged["actual"], errors="coerce")
        prediction = pd.to_numeric(merged["prediction"], errors="coerce")
        error = (actual - prediction).abs()
        negative_surprise = (prediction - actual).clip(lower=0)
        merged["readiness_forecast_error"] = error
        merged["readiness_absolute_forecast_error_score"] = np.where(error.notna(), normalize_series(error), np.nan)
        merged["readiness_forecast_error_score"] = np.where(negative_surprise.notna(), normalize_series(negative_surprise), np.nan)
        merged["readiness_model_pessimism_score"] = merged["readiness_forecast_error_score"]
    else:
        merged["readiness_forecast_error"] = np.nan
        merged["readiness_absolute_forecast_error_score"] = np.nan
        merged["readiness_forecast_error_score"] = np.nan
        merged["readiness_model_pessimism_score"] = np.nan

    reference = None
    if outcome_events_path is not None and outcome_events_path.exists() and z_cols:
        reference = load_reference_embedding(emb, outcome_events_path)

    similarities: list[float | None] = []
    similarity_scores: list[float | None] = []
    for _, row in merged.iterrows():
        if reference is None or not z_cols or pd.isna(row.get(z_cols[0])):
            similarities.append(None)
            similarity_scores.append(None)
            continue
        vector = np.array([row[column] for column in z_cols], dtype=float)
        similarity = cosine_similarity(vector, reference)
        similarities.append(similarity)
        similarity_scores.append(clamp(max(0.0, similarity) * 100.0))
    merged["reference_block_embedding_similarity"] = similarities
    merged["reference_block_similarity_score"] = similarity_scores

    novelty = pd.to_numeric(merged["embedding_novelty_score"], errors="coerce")
    forecast = pd.to_numeric(merged["readiness_forecast_error_score"], errors="coerce")
    similarity = pd.to_numeric(merged["reference_block_similarity_score"], errors="coerce")
    merged["frontier_strain_score"] = weighted_frontier_score(novelty, forecast, similarity)
    merged["accumulated_frontier_state"] = accumulated_frontier_state(merged)
    merged["accumulated_frontier_level"] = merged["accumulated_frontier_state"].map(
        lambda value: "high" if pd.notna(value) and value >= 70 else "moderate" if pd.notna(value) and value >= 45 else "low" if pd.notna(value) else None
    )

    bone = pd.to_numeric(merged.get("bone_stress_risk_score"), errors="coerce")
    integrated = (0.65 * bone + 0.35 * merged["accumulated_frontier_state"]).clip(0.0, 100.0)
    has_frontier = merged["accumulated_frontier_state"].notna()
    merged["integrated_bone_stress_score"] = np.where(has_frontier & bone.notna(), integrated, bone)
    merged["frontier_strain_level"] = merged["frontier_strain_score"].map(
        lambda value: "high" if pd.notna(value) and value >= 70 else "moderate" if pd.notna(value) and value >= 45 else "low" if pd.notna(value) else None
    )
    return merged
