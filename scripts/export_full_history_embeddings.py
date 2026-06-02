"""Export TCN embeddings and readiness predictions for full Garmin history."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / "outputs" / ".matplotlib"))

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

from src.modeling.contrastive import load_contrastive_encoder
from src.modeling.dataset import load_config
from src.modeling.inference import build_all_inference_windows, rolling_anomaly_scores
from src.modeling.tcn import AthleteStateTCN, TCNMaskedAutoencoder


def predict_pretrained_embeddings(
    model: torch.nn.Module,
    X: np.ndarray,
    device: torch.device,
    batch_size: int,
) -> np.ndarray:
    model.eval()
    embeddings = []
    loader = DataLoader(torch.from_numpy(X).float(), batch_size=batch_size, shuffle=False)
    with torch.no_grad():
        for X_batch in loader:
            _, z = model(X_batch.to(device))
            embeddings.append(z.cpu().numpy())
    return np.concatenate(embeddings)


def predict_contrastive_embeddings(
    model: torch.nn.Module,
    X: np.ndarray,
    device: torch.device,
    batch_size: int,
) -> np.ndarray:
    model.eval()
    embeddings = []
    loader = DataLoader(torch.from_numpy(X).float(), batch_size=batch_size, shuffle=False)
    with torch.no_grad():
        for X_batch in loader:
            z = model(X_batch.to(device))
            embeddings.append(z.cpu().numpy())
    return np.concatenate(embeddings)


def predict_finetuned(
    model: torch.nn.Module,
    X: np.ndarray,
    device: torch.device,
    batch_size: int,
) -> np.ndarray:
    model.eval()
    predictions = []
    loader = DataLoader(torch.from_numpy(X).float(), batch_size=batch_size, shuffle=False)
    with torch.no_grad():
        for X_batch in loader:
            pred, _ = model(X_batch.to(device))
            predictions.append(pred.cpu().numpy())
    return np.concatenate(predictions)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export full-history TCN embeddings and readiness predictions.")
    parser.add_argument("--config", type=Path, default=Path("config/model_features.json"))
    parser.add_argument(
        "--pretrained-checkpoint",
        type=Path,
        default=Path("outputs/modeling/masked_tcn/masked_tcn_pretrained.pt"),
    )
    parser.add_argument(
        "--finetuned-checkpoint",
        type=Path,
        default=Path("outputs/modeling/masked_tcn_finetuned/finetuned_masked_tcn_best.pt"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/modeling"))
    parser.add_argument(
        "--contrastive-checkpoint",
        type=Path,
        default=Path("outputs/modeling/contrastive_tcn/contrastive_encoder.pt"),
        help="Optional contrastive encoder checkpoint for injury-aware embeddings.",
    )
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()

    config = load_config(args.config)
    tcn_config = config.get("tcn", {})
    X, readiness, dates, splits, feature_names = build_all_inference_windows(config)
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

    pretrain_model = TCNMaskedAutoencoder(
        input_channels=len(feature_names),
        hidden_channels=int(tcn_config.get("hidden_channels", 32)),
        embedding_dim=int(tcn_config.get("embedding_dim", 16)),
        kernel_size=int(tcn_config.get("kernel_size", 3)),
        dilations=tcn_config.get("dilations", [1, 2, 4]),
        dropout=float(tcn_config.get("dropout", 0.15)),
    ).to(device)
    pretrain_checkpoint = torch.load(args.pretrained_checkpoint, map_location=device)
    pretrain_model.load_state_dict(pretrain_checkpoint["model_state_dict"])

    embedding_values = predict_pretrained_embeddings(pretrain_model, X, device, args.batch_size)
    anomaly_window = int(tcn_config.get("rolling_anomaly_window", 28))
    distances, zscores, norms = rolling_anomaly_scores(embedding_values, window=anomaly_window)

    embedding_rows = []
    for idx, date in enumerate(pd.to_datetime(dates)):
        row = {
            "split": str(splits[idx]),
            "date": pd.Timestamp(date).date().isoformat(),
        }
        row.update({f"z_{dim}": float(value) for dim, value in enumerate(embedding_values[idx])})
        row["embedding_distance"] = float(distances[idx])
        row["anomaly_zscore"] = float(zscores[idx])
        row["embedding_norm"] = float(norms[idx])
        row["embedding_drift"] = float(
            0.0 if idx == 0 else np.linalg.norm(embedding_values[idx] - embedding_values[idx - 1])
        )
        embedding_rows.append(row)
    embedding_frame = pd.DataFrame(embedding_rows).sort_values("date").reset_index(drop=True)

    finetune_model = AthleteStateTCN(
        input_channels=len(feature_names),
        hidden_channels=int(tcn_config.get("hidden_channels", 32)),
        embedding_dim=int(tcn_config.get("embedding_dim", 16)),
        kernel_size=int(tcn_config.get("kernel_size", 3)),
        dilations=tcn_config.get("dilations", [1, 2, 4]),
        dropout=float(tcn_config.get("dropout", 0.15)),
    ).to(device)
    finetune_checkpoint = torch.load(args.finetuned_checkpoint, map_location=device)
    finetune_model.load_state_dict(finetune_checkpoint["model_state_dict"])
    predictions = predict_finetuned(finetune_model, X, device, args.batch_size)

    prediction_rows = []
    for idx, date in enumerate(pd.to_datetime(dates)):
        actual = readiness[idx]
        prediction_rows.append(
            {
                "split": str(splits[idx]),
                "date": pd.Timestamp(date).date().isoformat(),
                "actual": float(actual) if not np.isnan(actual) else np.nan,
                "prediction": float(predictions[idx]),
            }
        )
    prediction_frame = pd.DataFrame(prediction_rows).sort_values("date").reset_index(drop=True)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    embedding_path = args.output_dir / "pretrained_embeddings.csv"
    prediction_path = args.output_dir / "masked_tcn_finetuned" / "finetuned_predictions.csv"
    prediction_path.parent.mkdir(parents=True, exist_ok=True)
    embedding_frame.to_csv(embedding_path, index=False)
    prediction_frame.to_csv(prediction_path, index=False)
    np.save(args.output_dir / "pretrained_embeddings.npy", embedding_values)

    contrastive_summary: dict[str, object] | None = None
    if args.contrastive_checkpoint.exists():
        contrastive_model, _ = load_contrastive_encoder(
            args.contrastive_checkpoint,
            args.pretrained_checkpoint,
            args.config,
            device,
        )
        contrastive_values = predict_contrastive_embeddings(contrastive_model, X, device, args.batch_size)
        c_distances, c_zscores, c_norms = rolling_anomaly_scores(contrastive_values, window=anomaly_window)
        contrastive_rows = []
        for idx, date in enumerate(pd.to_datetime(dates)):
            row = {
                "split": str(splits[idx]),
                "date": pd.Timestamp(date).date().isoformat(),
            }
            row.update({f"cz_{dim}": float(value) for dim, value in enumerate(contrastive_values[idx])})
            row["contrastive_embedding_distance"] = float(c_distances[idx])
            row["contrastive_anomaly_zscore"] = float(c_zscores[idx])
            row["contrastive_embedding_norm"] = float(c_norms[idx])
            contrastive_rows.append(row)
        contrastive_frame = pd.DataFrame(contrastive_rows).sort_values("date").reset_index(drop=True)
        contrastive_path = args.output_dir / "contrastive_embeddings.csv"
        contrastive_frame.to_csv(contrastive_path, index=False)
        np.save(args.output_dir / "contrastive_embeddings.npy", contrastive_values)
        contrastive_summary = {
            "windows_exported": int(len(contrastive_frame)),
            "embeddings_csv": str(contrastive_path),
        }

    summary = {
        "device": str(device),
        "windows_exported": int(len(embedding_frame)),
        "date_range": {
            "start": embedding_frame["date"].min(),
            "end": embedding_frame["date"].max(),
        },
        "readiness_labeled_days": int(prediction_frame["actual"].notna().sum()),
        "embeddings_csv": str(embedding_path),
        "predictions_csv": str(prediction_path),
        "contrastive": contrastive_summary,
    }
    summary_path = args.output_dir / "full_history_frontier_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
