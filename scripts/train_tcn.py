"""Train a lightweight TCN and export athlete-state embeddings."""

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
from sklearn.decomposition import PCA
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
    tensors = TensorDataset(torch.from_numpy(X).float(), torch.from_numpy(y).float())
    return DataLoader(tensors, batch_size=batch_size, shuffle=shuffle)


def evaluate(model: nn.Module, loader: DataLoader, loss_fn: nn.Module, device: torch.device) -> dict[str, float]:
    model.eval()
    losses = []
    predictions = []
    targets = []
    with torch.no_grad():
        for X_batch, y_batch in loader:
            X_batch = X_batch.to(device)
            y_batch = y_batch.to(device)
            pred, _ = model(X_batch)
            losses.append(loss_fn(pred, y_batch).item() * len(y_batch))
            predictions.append(pred.cpu().numpy())
            targets.append(y_batch.cpu().numpy())
    y_true = np.concatenate(targets)
    y_pred = np.concatenate(predictions)
    errors = y_pred - y_true
    return {
        "loss": float(sum(losses) / len(y_true)),
        "mae": float(np.mean(np.abs(errors))),
        "rmse": float(np.sqrt(np.mean(errors**2))),
    }


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


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    errors = y_pred - y_true
    return {
        "mae": float(np.mean(np.abs(errors))),
        "rmse": float(np.sqrt(np.mean(errors**2))),
        "n": int(len(y_true)),
    }


def rolling_anomaly_scores(embeddings: np.ndarray, window: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    distances = np.zeros(len(embeddings), dtype=float)
    zscores = np.zeros(len(embeddings), dtype=float)
    norms = np.linalg.norm(embeddings, axis=1)

    for idx in range(len(embeddings)):
        start = max(0, idx - window)
        history = embeddings[start:idx]
        if len(history) == 0:
            distances[idx] = 0.0
            zscores[idx] = 0.0
            continue
        baseline = history.mean(axis=0)
        distances[idx] = float(np.linalg.norm(embeddings[idx] - baseline))
        previous_distances = distances[start:idx]
        scale = previous_distances.std()
        zscores[idx] = 0.0 if scale == 0 else float((distances[idx] - previous_distances.mean()) / scale)
    return distances, zscores, norms


def save_training_curve(history: list[dict[str, float]], output_path: Path) -> None:
    frame = pd.DataFrame(history)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(frame["epoch"], frame["train_rmse"], label="Train RMSE")
    ax.plot(frame["epoch"], frame["val_rmse"], label="Validation RMSE")
    ax.set_title("TCN Training Curve")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("RMSE")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def save_prediction_plot(dates: np.ndarray, y_true: np.ndarray, y_pred: np.ndarray, output_path: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(12, 5))
    parsed_dates = pd.to_datetime(dates)
    ax.plot(parsed_dates, y_true, label="Actual", linewidth=2)
    ax.plot(parsed_dates, y_pred, label="TCN prediction", alpha=0.85)
    ax.set_title(title)
    ax.set_xlabel("Date")
    ax.set_ylabel("Next-day readiness score")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def save_anomaly_plots(frame: pd.DataFrame, output_dir: Path) -> None:
    parsed_dates = pd.to_datetime(frame["date"])
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(parsed_dates, frame["embedding_distance"], label="Distance from rolling baseline")
    ax.plot(parsed_dates, frame["anomaly_zscore"], label="Rolling z-score", alpha=0.8)
    ax.set_title("Latent Embedding Anomaly Scores")
    ax.set_xlabel("Date")
    ax.set_ylabel("Score")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / "tcn_anomaly_scores.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(parsed_dates, frame["embedding_norm"], label="Embedding norm")
    ax.plot(parsed_dates, frame["embedding_drift"], label="Day-to-day embedding drift", alpha=0.8)
    ax.set_title("Latent Embedding Norm And Drift")
    ax.set_xlabel("Date")
    ax.set_ylabel("Embedding magnitude")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / "tcn_embedding_norm_drift.png", dpi=160)
    plt.close(fig)


def save_pca_plot(embedding_frame: pd.DataFrame, output_path: Path) -> None:
    z_cols = [col for col in embedding_frame.columns if col.startswith("z_")]
    if len(z_cols) < 2:
        return
    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(embedding_frame[z_cols].to_numpy(dtype=float))
    fig, ax = plt.subplots(figsize=(7, 6))
    split_codes = embedding_frame["split"].map({"train": 0, "validation": 1, "test": 2}).to_numpy()
    scatter = ax.scatter(coords[:, 0], coords[:, 1], c=split_codes, s=18, alpha=0.75)
    ax.set_title("PCA Projection Of TCN Latent States")
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.grid(alpha=0.25)
    handles, _ = scatter.legend_elements()
    ax.legend(handles, ["train", "validation", "test"], title="Split")
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a TCN readiness forecaster and export embeddings.")
    parser.add_argument("--config", type=Path, default=Path("config/model_features.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/modeling/tcn"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    set_seed(args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    config = load_config(args.config)
    tcn_config = config.get("tcn", {})
    dataset = build_time_series_dataset(args.config)
    window_days = int(config.get("window_days", 28))
    feature_count = len(dataset.feature_names)

    X_train = reshape_for_tcn(dataset.X_train, window_days, feature_count)
    X_val = reshape_for_tcn(dataset.X_val, window_days, feature_count)
    X_test = reshape_for_tcn(dataset.X_test, window_days, feature_count)

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    batch_size = int(tcn_config.get("batch_size", 32))
    model = AthleteStateTCN(
        input_channels=feature_count,
        hidden_channels=int(tcn_config.get("hidden_channels", 32)),
        embedding_dim=int(tcn_config.get("embedding_dim", 16)),
        kernel_size=int(tcn_config.get("kernel_size", 3)),
        dilations=tcn_config.get("dilations", [1, 2, 4]),
        dropout=float(tcn_config.get("dropout", 0.15)),
    ).to(device)

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
    checkpoint_path = args.output_dir / "tcn_best.pt"

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

        train_metrics = evaluate(model, train_loader, loss_fn, device)
        val_metrics = evaluate(model, val_loader, loss_fn, device)
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
                    "config": tcn_config,
                    "feature_names": dataset.feature_names,
                    "target_name": dataset.target_name,
                    "window_days": window_days,
                    "best_epoch": best_epoch,
                    "best_val_rmse": best_val_rmse,
                },
                checkpoint_path,
            )
        elif epoch - best_epoch >= patience:
            break

    checkpoint = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(checkpoint["model_state_dict"])
    history_frame = pd.DataFrame(history)
    history_frame.to_csv(args.output_dir / "tcn_training_history.csv", index=False)
    save_training_curve(history, args.output_dir / "tcn_training_curve.png")

    all_splits = {
        "train": (X_train, dataset.y_train, dataset.dates_train),
        "validation": (X_val, dataset.y_val, dataset.dates_val),
        "test": (X_test, dataset.y_test, dataset.dates_test),
    }
    metrics: dict[str, dict[str, float]] = {}
    prediction_rows = []
    embedding_rows = []
    for split_name, (X_split, y_split, dates_split) in all_splits.items():
        pred, embeddings = predict_and_embed(model, X_split, device, batch_size)
        metrics[split_name] = regression_metrics(y_split, pred)
        for idx, date in enumerate(pd.to_datetime(dates_split)):
            prediction_rows.append(
                {
                    "split": split_name,
                    "date": date.date().isoformat(),
                    "actual": float(y_split[idx]),
                    "prediction": float(pred[idx]),
                }
            )
            row = {
                "split": split_name,
                "date": date.date().isoformat(),
                "target": float(y_split[idx]),
                "prediction": float(pred[idx]),
            }
            row.update({f"z_{dim}": float(value) for dim, value in enumerate(embeddings[idx])})
            embedding_rows.append(row)

    predictions = pd.DataFrame(prediction_rows)
    predictions.to_csv(args.output_dir / "tcn_predictions.csv", index=False)
    embeddings = pd.DataFrame(embedding_rows).sort_values("date").reset_index(drop=True)

    z_cols = [col for col in embeddings.columns if col.startswith("z_")]
    embedding_values = embeddings[z_cols].to_numpy(dtype=float)
    distances, zscores, norms = rolling_anomaly_scores(
        embedding_values,
        window=int(tcn_config.get("rolling_anomaly_window", 28)),
    )
    embeddings["embedding_distance"] = distances
    embeddings["anomaly_zscore"] = zscores
    embeddings["embedding_norm"] = norms
    embeddings["embedding_drift"] = np.r_[0.0, np.linalg.norm(np.diff(embedding_values, axis=0), axis=1)]
    embeddings.to_csv(args.output_dir / "embeddings.csv", index=False)
    np.save(args.output_dir / "embeddings.npy", embedding_values)
    if args.output_dir.name == "tcn":
        embeddings.to_csv(args.output_dir.parent / "embeddings.csv", index=False)
        np.save(args.output_dir.parent / "embeddings.npy", embedding_values)

    test_rows = predictions[predictions["split"] == "test"]
    save_prediction_plot(
        test_rows["date"].to_numpy(),
        test_rows["actual"].to_numpy(dtype=float),
        test_rows["prediction"].to_numpy(dtype=float),
        args.output_dir / "tcn_predictions_vs_actual_test.png",
        "TCN Predictions vs Actual Readiness (Test Split)",
    )
    val_rows = predictions[predictions["split"] == "validation"]
    save_prediction_plot(
        val_rows["date"].to_numpy(),
        val_rows["actual"].to_numpy(dtype=float),
        val_rows["prediction"].to_numpy(dtype=float),
        args.output_dir / "tcn_predictions_vs_actual_validation.png",
        "TCN Predictions vs Actual Readiness (Validation Split)",
    )
    save_anomaly_plots(embeddings, args.output_dir)
    save_pca_plot(embeddings, args.output_dir / "tcn_embedding_pca.png")

    summary = {
        "device": str(device),
        "best_epoch": int(best_epoch),
        "best_val_rmse": float(best_val_rmse),
        "metrics": metrics,
        "checkpoint": str(checkpoint_path),
        "embeddings_csv": str(args.output_dir / "embeddings.csv"),
        "embedding_dim": len(z_cols),
    }
    (args.output_dir / "tcn_metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
