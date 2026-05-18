"""Fine-tune readiness forecasting from a masked-pretrained TCN encoder."""

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
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from src.modeling.dataset import build_time_series_dataset, load_config
from src.modeling.tcn import AthleteStateTCN


def set_seed(seed: int) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)


def reshape_for_tcn(flat_windows: np.ndarray, window_days: int, feature_count: int) -> np.ndarray:
    return flat_windows.reshape(len(flat_windows), window_days, feature_count).transpose(0, 2, 1)


def make_loader(X: np.ndarray, y: np.ndarray, batch_size: int, shuffle: bool) -> DataLoader:
    return DataLoader(TensorDataset(torch.from_numpy(X).float(), torch.from_numpy(y).float()), batch_size=batch_size, shuffle=shuffle)


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    errors = y_pred - y_true
    return {"mae": float(np.mean(np.abs(errors))), "rmse": float(np.sqrt(np.mean(errors**2))), "n": int(len(y_true))}


def evaluate(model: nn.Module, loader: DataLoader, device: torch.device) -> dict[str, float]:
    model.eval()
    preds = []
    targets = []
    with torch.no_grad():
        for X_batch, y_batch in loader:
            pred, _ = model(X_batch.to(device))
            preds.append(pred.cpu().numpy())
            targets.append(y_batch.numpy())
    return regression_metrics(np.concatenate(targets), np.concatenate(preds))


def predict_and_embed(model: nn.Module, X: np.ndarray, device: torch.device, batch_size: int) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    preds = []
    embeddings = []
    loader = DataLoader(torch.from_numpy(X).float(), batch_size=batch_size, shuffle=False)
    with torch.no_grad():
        for X_batch in loader:
            pred, z = model(X_batch.to(device))
            preds.append(pred.cpu().numpy())
            embeddings.append(z.cpu().numpy())
    return np.concatenate(preds), np.concatenate(embeddings)


def save_curve(history: list[dict[str, float]], output_path: Path) -> None:
    frame = pd.DataFrame(history)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(frame["epoch"], frame["train_rmse"], label="Train RMSE")
    ax.plot(frame["epoch"], frame["val_rmse"], label="Validation RMSE")
    ax.set_title("Fine-tuned Masked TCN Training Curve")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("RMSE")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def save_prediction_plot(dates: np.ndarray, y_true: np.ndarray, y_pred: np.ndarray, output_path: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(pd.to_datetime(dates), y_true, label="Actual", linewidth=2)
    ax.plot(pd.to_datetime(dates), y_pred, label="Fine-tuned masked TCN", alpha=0.85)
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
    parser = argparse.ArgumentParser(description="Fine-tune TCN readiness model from masked pretraining.")
    parser.add_argument("--config", type=Path, default=Path("config/model_features.json"))
    parser.add_argument("--checkpoint", type=Path, default=Path("outputs/modeling/masked_tcn/masked_tcn_pretrained.pt"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/modeling/masked_tcn_finetuned"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    set_seed(args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    config = load_config(args.config)
    tcn_config = config.get("tcn", {})
    dataset = build_time_series_dataset(args.config)
    window_days = int(config.get("window_days", 28))
    feature_count = len(dataset.feature_names)
    batch_size = int(tcn_config.get("batch_size", 32))

    X_train = reshape_for_tcn(dataset.X_train, window_days, feature_count)
    X_val = reshape_for_tcn(dataset.X_val, window_days, feature_count)
    X_test = reshape_for_tcn(dataset.X_test, window_days, feature_count)
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

    model = AthleteStateTCN(
        input_channels=feature_count,
        hidden_channels=int(tcn_config.get("hidden_channels", 32)),
        embedding_dim=int(tcn_config.get("embedding_dim", 16)),
        kernel_size=int(tcn_config.get("kernel_size", 3)),
        dilations=tcn_config.get("dilations", [1, 2, 4]),
        dropout=float(tcn_config.get("dropout", 0.15)),
    ).to(device)
    checkpoint = torch.load(args.checkpoint, map_location=device)
    model.encoder.load_state_dict(checkpoint["encoder_state_dict"])

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=float(tcn_config.get("learning_rate", 1e-3)),
        weight_decay=float(tcn_config.get("weight_decay", 1e-4)),
    )
    loss_fn = nn.MSELoss()
    train_loader = make_loader(X_train, dataset.y_train, batch_size=batch_size, shuffle=True)
    val_loader = make_loader(X_val, dataset.y_val, batch_size=batch_size, shuffle=False)

    max_epochs = int(tcn_config.get("max_epochs", 300))
    patience = int(tcn_config.get("early_stopping_patience", 30))
    best_val_rmse = float("inf")
    best_epoch = 0
    history = []
    best_path = args.output_dir / "finetuned_masked_tcn_best.pt"

    for epoch in range(1, max_epochs + 1):
        model.train()
        for X_batch, y_batch in train_loader:
            X_batch = X_batch.to(device)
            y_batch = y_batch.to(device)
            optimizer.zero_grad()
            pred, _ = model(X_batch)
            loss = loss_fn(pred, y_batch)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

        train_metrics = evaluate(model, train_loader, device)
        val_metrics = evaluate(model, val_loader, device)
        history.append(
            {
                "epoch": epoch,
                "train_mae": train_metrics["mae"],
                "train_rmse": train_metrics["rmse"],
                "val_mae": val_metrics["mae"],
                "val_rmse": val_metrics["rmse"],
            }
        )
        if val_metrics["rmse"] < best_val_rmse:
            best_val_rmse = val_metrics["rmse"]
            best_epoch = epoch
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "pretrained_checkpoint": str(args.checkpoint),
                    "best_epoch": best_epoch,
                    "best_val_rmse": best_val_rmse,
                    "feature_names": dataset.feature_names,
                },
                best_path,
            )
        elif epoch - best_epoch >= patience:
            break

    best = torch.load(best_path, map_location=device)
    model.load_state_dict(best["model_state_dict"])
    pd.DataFrame(history).to_csv(args.output_dir / "finetune_history.csv", index=False)
    save_curve(history, args.output_dir / "finetune_training_curve.png")

    splits = {
        "train": (X_train, dataset.y_train, dataset.dates_train),
        "validation": (X_val, dataset.y_val, dataset.dates_val),
        "test": (X_test, dataset.y_test, dataset.dates_test),
    }
    metrics = {}
    rows = []
    embedding_rows = []
    for split_name, (X_split, y_split, dates_split) in splits.items():
        pred, embeddings = predict_and_embed(model, X_split, device, batch_size)
        metrics[split_name] = regression_metrics(y_split, pred)
        for idx, date in enumerate(pd.to_datetime(dates_split)):
            rows.append({"split": split_name, "date": date.date().isoformat(), "actual": float(y_split[idx]), "prediction": float(pred[idx])})
            row = {"split": split_name, "date": date.date().isoformat(), "target": float(y_split[idx]), "prediction": float(pred[idx])}
            row.update({f"z_{dim}": float(value) for dim, value in enumerate(embeddings[idx])})
            embedding_rows.append(row)

    predictions = pd.DataFrame(rows)
    predictions.to_csv(args.output_dir / "finetuned_predictions.csv", index=False)
    pd.DataFrame(embedding_rows).to_csv(args.output_dir / "finetuned_embeddings.csv", index=False)
    test_rows = predictions[predictions["split"] == "test"]
    save_prediction_plot(
        test_rows["date"].to_numpy(),
        test_rows["actual"].to_numpy(dtype=float),
        test_rows["prediction"].to_numpy(dtype=float),
        args.output_dir / "finetuned_predictions_vs_actual_test.png",
        "Fine-tuned Masked TCN Predictions vs Actual Readiness (Test Split)",
    )

    supervised_metrics_path = Path("outputs/modeling/tcn/tcn_metrics.json")
    supervised_comparison = None
    if supervised_metrics_path.exists():
        supervised_comparison = json.loads(supervised_metrics_path.read_text(encoding="utf-8")).get("metrics", {})

    summary = {
        "device": str(device),
        "best_epoch": int(best_epoch),
        "best_val_rmse": float(best_val_rmse),
        "metrics": metrics,
        "supervised_tcn_metrics": supervised_comparison,
        "checkpoint": str(best_path),
    }
    (args.output_dir / "finetune_metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
