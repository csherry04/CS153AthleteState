"""Train and evaluate simple recovery/readiness baselines."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / "outputs" / ".matplotlib"))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor

from src.modeling.dataset import build_time_series_dataset


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    if mask.sum() == 0:
        return {"mae": float("nan"), "rmse": float("nan"), "n": 0}
    errors = y_pred[mask] - y_true[mask]
    return {
        "mae": float(np.mean(np.abs(errors))),
        "rmse": float(np.sqrt(np.mean(errors**2))),
        "n": int(mask.sum()),
    }


def save_prediction_plot(
    dates: np.ndarray,
    y_true: np.ndarray,
    predictions: dict[str, np.ndarray],
    output_path: Path,
    title: str,
) -> None:
    fig, ax = plt.subplots(figsize=(12, 5))
    parsed_dates = pd.to_datetime(dates)
    ax.plot(parsed_dates, y_true, label="Actual", linewidth=2)
    for name, pred in predictions.items():
        ax.plot(parsed_dates, pred, label=name, alpha=0.8)
    ax.set_title(title)
    ax.set_xlabel("Date")
    ax.set_ylabel("Next-day readiness score")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train baseline models for next-day readiness.")
    parser.add_argument("--config", type=Path, default=Path("config/model_features.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/modeling"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    dataset = build_time_series_dataset(args.config)

    ridge = Ridge(alpha=10.0)
    ridge.fit(dataset.X_train, dataset.y_train)

    mlp = MLPRegressor(
        hidden_layer_sizes=(64, 32),
        activation="relu",
        alpha=1e-3,
        learning_rate_init=1e-3,
        max_iter=1000,
        early_stopping=True,
        random_state=42,
    )
    mlp.fit(dataset.X_train, dataset.y_train)

    predictions = {
        "naive_persistence": {
            "train": dataset.persistence_train,
            "validation": dataset.persistence_val,
            "test": dataset.persistence_test,
        },
        "ridge": {
            "train": ridge.predict(dataset.X_train),
            "validation": ridge.predict(dataset.X_val),
            "test": ridge.predict(dataset.X_test),
        },
        "mlp": {
            "train": mlp.predict(dataset.X_train),
            "validation": mlp.predict(dataset.X_val),
            "test": mlp.predict(dataset.X_test),
        },
    }

    metrics: dict[str, dict[str, dict[str, float]]] = {}
    splits = {
        "train": (dataset.y_train, dataset.dates_train),
        "validation": (dataset.y_val, dataset.dates_val),
        "test": (dataset.y_test, dataset.dates_test),
    }
    for model_name, model_predictions in predictions.items():
        metrics[model_name] = {}
        for split_name, (y_true, _) in splits.items():
            metrics[model_name][split_name] = regression_metrics(y_true, model_predictions[split_name])

    (args.output_dir / "baseline_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    test_predictions = {name: values["test"] for name, values in predictions.items()}
    save_prediction_plot(
        dataset.dates_test,
        dataset.y_test,
        test_predictions,
        args.output_dir / "predicted_vs_actual_test.png",
        "Baseline Predictions vs Actual Readiness (Test Split)",
    )
    validation_predictions = {name: values["validation"] for name, values in predictions.items()}
    save_prediction_plot(
        dataset.dates_val,
        dataset.y_val,
        validation_predictions,
        args.output_dir / "predicted_vs_actual_validation.png",
        "Baseline Predictions vs Actual Readiness (Validation Split)",
    )

    prediction_rows = []
    for split_name, (y_true, dates) in splits.items():
        for idx, date in enumerate(pd.to_datetime(dates)):
            row = {"split": split_name, "date": date.date().isoformat(), "actual": float(y_true[idx])}
            for model_name, model_predictions in predictions.items():
                pred = model_predictions[split_name][idx]
                row[model_name] = None if not np.isfinite(pred) else float(pred)
            prediction_rows.append(row)
    pd.DataFrame(prediction_rows).to_csv(args.output_dir / "baseline_predictions.csv", index=False)

    print(json.dumps(metrics, indent=2))
    print(f"Wrote baseline outputs to {args.output_dir}")


if __name__ == "__main__":
    main()
