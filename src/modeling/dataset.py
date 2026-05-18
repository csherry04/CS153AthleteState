"""Time-series dataset construction for athlete-state baselines."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class TimeSeriesDataset:
    dates: np.ndarray
    feature_names: list[str]
    target_name: str
    X_train: np.ndarray
    y_train: np.ndarray
    dates_train: np.ndarray
    X_val: np.ndarray
    y_val: np.ndarray
    dates_val: np.ndarray
    X_test: np.ndarray
    y_test: np.ndarray
    dates_test: np.ndarray
    persistence_train: np.ndarray
    persistence_val: np.ndarray
    persistence_test: np.ndarray
    train_mean: np.ndarray
    train_std: np.ndarray
    impute_values: pd.Series


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_daily_frame(data_path: Path, date_column: str = "date") -> pd.DataFrame:
    frame = pd.read_csv(data_path, parse_dates=[date_column])
    frame = frame.sort_values(date_column).drop_duplicates(date_column, keep="last")
    full_dates = pd.date_range(frame[date_column].min(), frame[date_column].max(), freq="D")
    frame = frame.set_index(date_column).reindex(full_dates)
    frame.index.name = date_column
    return frame.reset_index()


def available_features(frame: pd.DataFrame, requested_features: list[str], target_column: str) -> list[str]:
    features = [feature for feature in requested_features if feature in frame.columns]
    if target_column not in features and target_column in frame.columns:
        features.append(target_column)
    return features


def chronological_split_indices(n_rows: int, train_fraction: float, validation_fraction: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    train_end = int(n_rows * train_fraction)
    val_end = train_end + int(n_rows * validation_fraction)
    indices = np.arange(n_rows)
    return indices[:train_end], indices[train_end:val_end], indices[val_end:]


def fit_preprocessor(train_values: pd.DataFrame) -> tuple[pd.Series, np.ndarray, np.ndarray]:
    impute_values = train_values.median(numeric_only=True).fillna(0.0)
    imputed = train_values.fillna(impute_values)
    mean = imputed.mean(axis=0).to_numpy(dtype=float)
    std = imputed.std(axis=0, ddof=0).replace(0, 1.0).fillna(1.0).to_numpy(dtype=float)
    return impute_values, mean, std


def transform_features(values: pd.DataFrame, impute_values: pd.Series, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    numeric = values.apply(pd.to_numeric, errors="coerce")
    imputed = numeric.fillna(impute_values)
    return ((imputed.to_numpy(dtype=float) - mean) / std).astype(np.float32)


def make_windows(
    transformed: np.ndarray,
    raw_target: pd.Series,
    dates: pd.Series,
    target_feature_index: int,
    window_days: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    windows = []
    targets = []
    target_dates = []
    persistence = []

    target_values = pd.to_numeric(raw_target, errors="coerce").to_numpy(dtype=float)
    date_values = dates.to_numpy()
    for target_idx in range(window_days, len(transformed)):
        target = target_values[target_idx]
        if np.isnan(target):
            continue
        start = target_idx - window_days
        window = transformed[start:target_idx]
        windows.append(window.reshape(-1))
        targets.append(target)
        target_dates.append(date_values[target_idx])
        previous_targets = target_values[start:target_idx]
        observed_previous_targets = previous_targets[~np.isnan(previous_targets)]
        persistence.append(observed_previous_targets[-1] if len(observed_previous_targets) else np.nan)

    return (
        np.asarray(windows, dtype=np.float32),
        np.asarray(targets, dtype=np.float32),
        np.asarray(target_dates),
        np.asarray(persistence, dtype=np.float32),
    )


def build_time_series_dataset(config_path: Path = Path("config/model_features.json")) -> TimeSeriesDataset:
    config = load_config(config_path)
    date_column = config.get("date_column", "date")
    target_column = config["target_column"]
    window_days = int(config.get("window_days", 28))
    split = config.get("split", {})

    frame = load_daily_frame(Path(config["data_path"]), date_column=date_column)
    if target_column not in frame.columns:
        raise ValueError(f"Target column {target_column!r} is missing from {config['data_path']}")

    feature_names = available_features(frame, config["features"], target_column)
    numeric_features = frame[feature_names].apply(pd.to_numeric, errors="coerce")

    target_values = pd.to_numeric(frame[target_column], errors="coerce")
    valid_target_indices = np.asarray(
        [idx for idx in range(window_days, len(frame)) if not pd.isna(target_values.iloc[idx])],
        dtype=int,
    )
    if len(valid_target_indices) == 0:
        raise ValueError(f"No non-null {target_column!r} targets are available after {window_days} days.")

    train_end = int(len(valid_target_indices) * float(split.get("train_fraction", 0.7)))
    val_end = train_end + int(len(valid_target_indices) * float(split.get("validation_fraction", 0.15)))
    train_end = max(train_end, 1)
    val_end = max(val_end, train_end + 1) if len(valid_target_indices) > train_end else train_end
    train_target_indices = valid_target_indices[:train_end]

    # Fit preprocessing only on rows that could have appeared in training windows.
    scaler_fit_end = int(train_target_indices[-1])
    impute_values, train_mean, train_std = fit_preprocessor(numeric_features.iloc[:scaler_fit_end])
    transformed = transform_features(numeric_features, impute_values, train_mean, train_std)
    target_feature_index = feature_names.index(target_column)
    X, y, target_dates, persistence = make_windows(
        transformed,
        frame[target_column],
        frame[date_column],
        target_feature_index=target_feature_index,
        window_days=window_days,
    )
    train_slice = slice(0, train_end)
    val_slice = slice(train_end, val_end)
    test_slice = slice(val_end, None)

    return TimeSeriesDataset(
        dates=target_dates,
        feature_names=feature_names,
        target_name=target_column,
        X_train=X[train_slice],
        y_train=y[train_slice],
        dates_train=target_dates[train_slice],
        X_val=X[val_slice],
        y_val=y[val_slice],
        dates_val=target_dates[val_slice],
        X_test=X[test_slice],
        y_test=y[test_slice],
        dates_test=target_dates[test_slice],
        persistence_train=persistence[train_slice],
        persistence_val=persistence[val_slice],
        persistence_test=persistence[test_slice],
        train_mean=train_mean,
        train_std=train_std,
        impute_values=impute_values,
    )
