"""Dataset helpers for masked temporal reconstruction pretraining."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.modeling.dataset import available_features, fit_preprocessor, load_daily_frame, transform_features


@dataclass
class ReconstructionDataset:
    feature_names: list[str]
    X_train: np.ndarray
    observed_train: np.ndarray
    dates_train: np.ndarray
    X_val: np.ndarray
    observed_val: np.ndarray
    dates_val: np.ndarray
    X_test: np.ndarray
    observed_test: np.ndarray
    dates_test: np.ndarray
    train_mean: np.ndarray
    train_std: np.ndarray
    impute_values: pd.Series


def split_valid_target_indices(frame: pd.DataFrame, target_column: str, window_days: int, split: dict[str, Any]) -> tuple[np.ndarray, int, int]:
    target_values = pd.to_numeric(frame[target_column], errors="coerce")
    valid_target_indices = np.asarray(
        [idx for idx in range(window_days, len(frame)) if not pd.isna(target_values.iloc[idx])],
        dtype=int,
    )
    if len(valid_target_indices) == 0:
        raise ValueError(f"No non-null {target_column!r} targets are available after {window_days} days.")
    train_end = max(int(len(valid_target_indices) * float(split.get("train_fraction", 0.7))), 1)
    val_end = train_end + int(len(valid_target_indices) * float(split.get("validation_fraction", 0.15)))
    if len(valid_target_indices) > train_end:
        val_end = max(val_end, train_end + 1)
    return valid_target_indices, train_end, val_end


def make_reconstruction_windows(
    transformed: np.ndarray,
    observed: np.ndarray,
    dates: pd.Series,
    target_indices: np.ndarray,
    window_days: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    windows = []
    observed_windows = []
    window_dates = []
    date_values = dates.to_numpy()
    for target_idx in target_indices:
        start = target_idx - window_days
        windows.append(transformed[start:target_idx])
        observed_windows.append(observed[start:target_idx])
        window_dates.append(date_values[target_idx])
    X = np.asarray(windows, dtype=np.float32).transpose(0, 2, 1)
    observed_mask = np.asarray(observed_windows, dtype=bool).transpose(0, 2, 1)
    return X, observed_mask, np.asarray(window_dates)


def build_reconstruction_dataset(config: dict[str, Any]) -> ReconstructionDataset:
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
    X, observed_windows, dates = make_reconstruction_windows(
        transformed=transformed,
        observed=observed,
        dates=frame[date_column],
        target_indices=valid_indices,
        window_days=window_days,
    )

    return ReconstructionDataset(
        feature_names=feature_names,
        X_train=X[:train_end],
        observed_train=observed_windows[:train_end],
        dates_train=dates[:train_end],
        X_val=X[train_end:val_end],
        observed_val=observed_windows[train_end:val_end],
        dates_val=dates[train_end:val_end],
        X_test=X[val_end:],
        observed_test=observed_windows[val_end:],
        dates_test=dates[val_end:],
        train_mean=train_mean,
        train_std=train_std,
        impute_values=impute_values,
    )
