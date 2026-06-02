"""Reference embedding archetypes for frontier interpretability."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ReferenceArchetype:
    id: str
    label: str
    description: str
    centroid: np.ndarray


def embedding_columns(frame: pd.DataFrame) -> list[str]:
    return [column for column in frame.columns if column.startswith("z_")]


def centroid_for_dates(embeddings: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> np.ndarray | None:
    z_cols = embedding_columns(embeddings)
    if not z_cols:
        return None
    window = embeddings[(embeddings["date"] >= start) & (embeddings["date"] <= end)]
    if window.empty:
        return None
    return window[z_cols].to_numpy(dtype=float).mean(axis=0)


def build_reference_archetypes(
    embeddings: pd.DataFrame,
    bone_scores: pd.DataFrame,
    outcome_events_path: Path,
    bone_periods: pd.DataFrame | None = None,
) -> list[ReferenceArchetype]:
    emb = embeddings.copy()
    emb["date"] = pd.to_datetime(emb["date"])
    archetypes: list[ReferenceArchetype] = []
    payload = json.loads(outcome_events_path.read_text(encoding="utf-8")) if outcome_events_path.exists() else {}

    for event in payload.get("events", []):
        start = pd.Timestamp(event.get("symptom_window_start") or event.get("onset_date"))
        end = pd.Timestamp(event.get("onset_date")) + pd.Timedelta(days=14)
        centroid = centroid_for_dates(emb, start, end)
        if centroid is not None:
            archetypes.append(
                ReferenceArchetype(
                    id=f"event_{event['id']}",
                    label=str(event.get("label", event["id"])),
                    description="Mean latent state during labeled pre-onset window (validation reference).",
                    centroid=centroid,
                )
            )

    for ref in payload.get("reference_periods", []):
        start = pd.Timestamp(ref["start_date"])
        end = pd.Timestamp(ref["end_date"])
        centroid = centroid_for_dates(emb, start, end)
        if centroid is not None:
            archetypes.append(
                ReferenceArchetype(
                    id=str(ref["id"]),
                    label=str(ref.get("label", ref["id"])),
                    description=str(ref.get("description", "Configured reference load block.")),
                    centroid=centroid,
                )
            )

    if bone_periods is not None and not bone_periods.empty:
        periods = bone_periods.copy()
        if "start_date" in periods.columns:
            periods["start_date"] = pd.to_datetime(periods["start_date"])
            periods["end_date"] = pd.to_datetime(periods["end_date"])
        top = periods.sort_values("peak_accumulated_bone_stress_state", ascending=False).head(2)
        for _, period in top.iterrows():
            centroid = centroid_for_dates(emb, period["start_date"], period["end_date"])
            if centroid is None:
                continue
            archetypes.append(
                ReferenceArchetype(
                    id=f"period_{int(period.get('period_id', 0))}",
                    label=f"High load block {period['start_date'].date()}",
                    description=str(period.get("dominant_bone_stress_reason", "Detected high-load period")),
                    centroid=centroid,
                )
            )

    bone = bone_scores.copy()
    bone["date"] = pd.to_datetime(bone["date"])
    stable = bone[
        (bone["bone_stress_risk_level"] == "low")
        & (bone["running_7d_sum_m"].fillna(0) > 20_000)
        & bone["date"].between(bone["date"].min(), bone["date"].max())
    ]
    if len(stable) >= 14:
        sample = stable.sort_values("running_7d_sum_m", ascending=False).head(28)
        z_cols = embedding_columns(emb)
        merged = sample[["date"]].merge(emb[["date", *z_cols]], on="date", how="inner")
        if not merged.empty and z_cols:
            archetypes.append(
                ReferenceArchetype(
                    id="stable_high_volume",
                    label="Stable high-volume running",
                    description="Embedding centroid during low-alert weeks with substantial running.",
                    centroid=merged[z_cols].to_numpy(dtype=float).mean(axis=0),
                )
            )

    return archetypes


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom <= 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def match_archetypes(
    vector: np.ndarray,
    archetypes: list[ReferenceArchetype],
) -> tuple[str | None, float | None, str | None]:
    if not archetypes:
        return None, None, None
    best_id = None
    best_label = None
    best_score = -1.0
    for archetype in archetypes:
        score = max(0.0, cosine_similarity(vector, archetype.centroid))
        if score > best_score:
            best_score = score
            best_id = archetype.id
            best_label = archetype.label
    return best_id, best_score * 100.0, best_label
