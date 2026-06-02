"""Full-history TCN inference windows using training-fit preprocessing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.modeling.dataset import available_features, fit_preprocessor, load_daily_frame, transform_features
from src.modeling.pretraining import make_reconstruction_windows, split_valid_target_indices


def rolling_anomaly_scores(embeddings: np.ndarray, window: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    distances = np.zeros(len(embeddings), dtype=float)
    zscores = np.zeros(len(embeddings), dtype=float)
    norms = np.linalg.norm(embeddings, axis=1)
    for idx in range(len(embeddings)):
        start = max(0, idx - window)
        history = embeddings[start:idx]
        if len(history) == 0:
            continue
        baseline = history.mean(axis=0)
        distances[idx] = float(np.linalg.norm(embeddings[idx] - baseline))
        prior = distances[start:idx]
        scale = prior.std()
        zscores[idx] = 0.0 if scale == 0 else float((distances[idx] - prior.mean()) / scale)
    return distances, zscores, norms


def build_all_inference_windows(config: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str]]:
    """Build a 28-day window for every day after the lookback, not only readiness-labeled days."""
    date_column = config.get("date_column", "date")
    target_column = config["target_column"]
    window_days = int(config.get("window_days", 28))
    split = config.get("split", {})

    frame = load_daily_frame(Path(config["data_path"]), date_column=date_column)
    feature_names = available_features(frame, config["features"], target_column)
    numeric_features = frame[feature_names].apply(pd.to_numeric, errors="coerce")
    observed = numeric_features.notna().to_numpy()

    valid_indices, train_end, val_end = split_valid_target_indices(frame, target_column, window_days, split)
    train_target_indices = valid_indices[:train_end]
    scaler_fit_end = int(train_target_indices[-1])
    impute_values, train_mean, train_std = fit_preprocessor(numeric_features.iloc[:scaler_fit_end])
    transformed = transform_features(numeric_features, impute_values, train_mean, train_std)

    all_target_indices = np.arange(window_days, len(frame), dtype=int)
    X, _, dates = make_reconstruction_windows(
        transformed=transformed,
        observed=observed,
        dates=frame[date_column],
        target_indices=all_target_indices,
        window_days=window_days,
    )
    target_values = pd.to_numeric(frame[target_column], errors="coerce").to_numpy(dtype=float)
    readiness = target_values[all_target_indices]

    index_to_split_pos = {int(idx): pos for pos, idx in enumerate(valid_indices)}
    splits = []
    for idx in all_target_indices:
        pos = index_to_split_pos.get(int(idx))
        if pos is None:
            splits.append("historical")
        elif pos < train_end:
            splits.append("train")
        elif pos < val_end:
            splits.append("validation")
        else:
            splits.append("test")

    return X, readiness, dates, np.asarray(splits), feature_names
