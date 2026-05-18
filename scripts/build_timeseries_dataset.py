"""Build and summarize the 28-day sliding-window modeling dataset."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.modeling.dataset import build_time_series_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Build time-series train/validation/test windows.")
    parser.add_argument("--config", type=Path, default=Path("config/model_features.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/modeling"))
    args = parser.parse_args()

    dataset = build_time_series_dataset(args.config)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    np.savez_compressed(
        args.output_dir / "timeseries_dataset.npz",
        X_train=dataset.X_train,
        y_train=dataset.y_train,
        dates_train=dataset.dates_train.astype("datetime64[D]").astype(str),
        X_val=dataset.X_val,
        y_val=dataset.y_val,
        dates_val=dataset.dates_val.astype("datetime64[D]").astype(str),
        X_test=dataset.X_test,
        y_test=dataset.y_test,
        dates_test=dataset.dates_test.astype("datetime64[D]").astype(str),
        persistence_train=dataset.persistence_train,
        persistence_val=dataset.persistence_val,
        persistence_test=dataset.persistence_test,
        feature_names=np.asarray(dataset.feature_names),
        target_name=np.asarray(dataset.target_name),
    )

    summary = {
        "target": dataset.target_name,
        "feature_count": len(dataset.feature_names),
        "windowed_feature_count": int(dataset.X_train.shape[1]) if len(dataset.X_train) else 0,
        "train_windows": int(len(dataset.y_train)),
        "validation_windows": int(len(dataset.y_val)),
        "test_windows": int(len(dataset.y_test)),
        "train_date_min": str(dataset.dates_train.min())[:10] if len(dataset.dates_train) else None,
        "train_date_max": str(dataset.dates_train.max())[:10] if len(dataset.dates_train) else None,
        "validation_date_min": str(dataset.dates_val.min())[:10] if len(dataset.dates_val) else None,
        "validation_date_max": str(dataset.dates_val.max())[:10] if len(dataset.dates_val) else None,
        "test_date_min": str(dataset.dates_test.min())[:10] if len(dataset.dates_test) else None,
        "test_date_max": str(dataset.dates_test.max())[:10] if len(dataset.dates_test) else None,
        "features": dataset.feature_names,
    }
    (args.output_dir / "dataset_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
