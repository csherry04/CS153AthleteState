"""Nearest-neighbor and archetype explanations for frontier embeddings."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.reference_archetypes import build_reference_archetypes, embedding_columns, match_archetypes


def nearest_neighbor_dates(
    embeddings: pd.DataFrame,
    target_date: pd.Timestamp,
    k: int = 3,
    exclude_days: int = 7,
) -> list[dict[str, object]]:
    z_cols = embedding_columns(embeddings)
    if not z_cols:
        return []
    frame = embeddings.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    target_rows = frame[frame["date"] == target_date]
    if target_rows.empty or pd.isna(target_rows.iloc[0].get(z_cols[0])):
        return []

    target = target_rows.iloc[0]
    vector = target[z_cols].to_numpy(dtype=float)
    history = frame[frame["date"] < target_date - pd.Timedelta(days=exclude_days)]
    history = history[history[z_cols[0]].notna()]
    if history.empty:
        return []

    distances = np.linalg.norm(history[z_cols].to_numpy(dtype=float) - vector, axis=1)
    nearest = history.assign(neighbor_distance=distances).nsmallest(k, "neighbor_distance")
    rows: list[dict[str, object]] = []
    for _, row in nearest.iterrows():
        rows.append(
            {
                "date": row["date"].date().isoformat(),
                "distance": float(row["neighbor_distance"]),
            }
        )
    return rows


def neighbor_summary(neighbors: list[dict[str, object]]) -> str | None:
    if not neighbors:
        return None
    dates = ", ".join(str(item["date"]) for item in neighbors[:3])
    return f"Latent state resembles {dates}."


def enrich_embedding_explanations(
    scores: pd.DataFrame,
    embeddings: pd.DataFrame,
    outcome_events_path: Path,
    bone_periods: pd.DataFrame | None = None,
) -> pd.DataFrame:
    enriched = scores.copy()
    enriched["date"] = pd.to_datetime(enriched["date"])
    emb = embeddings.copy()
    emb["date"] = pd.to_datetime(emb["date"])
    z_cols = embedding_columns(emb)
    archetypes = build_reference_archetypes(emb, enriched, outcome_events_path, bone_periods)

    archetype_ids: list[str | None] = []
    archetype_labels: list[str | None] = []
    archetype_scores: list[float | None] = []
    neighbor_summaries: list[str | None] = []

    for _, row in enriched.iterrows():
        if not z_cols or pd.isna(row.get("anomaly_zscore")):
            archetype_ids.append(None)
            archetype_labels.append(None)
            archetype_scores.append(None)
            neighbor_summaries.append(None)
            continue
        merged_row = emb[emb["date"] == row["date"]]
        if merged_row.empty:
            archetype_ids.append(None)
            archetype_labels.append(None)
            archetype_scores.append(None)
            neighbor_summaries.append(None)
            continue
        vector = merged_row.iloc[0][z_cols].to_numpy(dtype=float)
        best_id, best_score, best_label = match_archetypes(vector, archetypes)
        neighbors = nearest_neighbor_dates(emb, row["date"], k=3)
        archetype_ids.append(best_id)
        archetype_labels.append(best_label)
        archetype_scores.append(best_score)
        neighbor_summaries.append(neighbor_summary(neighbors))

    enriched["reference_archetype_id"] = archetype_ids
    enriched["reference_archetype_label"] = archetype_labels
    enriched["reference_archetype_score"] = archetype_scores
    enriched["embedding_neighbor_summary"] = neighbor_summaries
    return enriched
