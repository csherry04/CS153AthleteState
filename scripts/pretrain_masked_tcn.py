"""Masked reconstruction pretraining for the TCN temporal encoder."""

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
from sklearn.decomposition import PCA

from src.modeling.dataset import load_config
from src.modeling.pretraining import build_reconstruction_dataset
from src.modeling.tcn import TCNMaskedAutoencoder


def set_seed(seed: int) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)


def make_loader(X: np.ndarray, observed: np.ndarray, batch_size: int, shuffle: bool) -> DataLoader:
    tensors = TensorDataset(torch.from_numpy(X).float(), torch.from_numpy(observed.astype(np.float32)))
    return DataLoader(tensors, batch_size=batch_size, shuffle=shuffle)


def masked_reconstruction_loss(
    reconstruction: torch.Tensor,
    original: torch.Tensor,
    observed: torch.Tensor,
    mask_fraction: float,
) -> tuple[torch.Tensor, torch.Tensor]:
    random_mask = (torch.rand_like(original) < mask_fraction) & (observed > 0)
    if random_mask.sum() == 0:
        random_mask = observed > 0
    masked_positions = random_mask.float()
    loss = ((reconstruction - original) ** 2 * masked_positions).sum() / masked_positions.sum().clamp_min(1.0)
    return loss, random_mask


def apply_random_mask(original: torch.Tensor, observed: torch.Tensor, mask_fraction: float) -> tuple[torch.Tensor, torch.Tensor]:
    random_mask = (torch.rand_like(original) < mask_fraction) & (observed > 0)
    if random_mask.sum() == 0:
        random_mask = observed > 0
    masked = original.clone()
    masked[random_mask] = 0.0
    return masked, random_mask


def evaluate(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    mask_fraction: float,
) -> dict[str, float]:
    model.eval()
    total_loss = 0.0
    total_positions = 0.0
    with torch.no_grad():
        for X_batch, observed_batch in loader:
            X_batch = X_batch.to(device)
            observed_batch = observed_batch.to(device)
            masked_batch, masked_positions = apply_random_mask(X_batch, observed_batch, mask_fraction)
            reconstruction, _ = model(masked_batch)
            position_count = masked_positions.float().sum().clamp_min(1.0)
            loss = ((reconstruction - X_batch) ** 2 * masked_positions.float()).sum()
            total_loss += float(loss.item())
            total_positions += float(position_count.item())
    mse = total_loss / max(total_positions, 1.0)
    return {"mse": mse, "rmse": float(np.sqrt(mse))}


def predict_embeddings(model: nn.Module, X: np.ndarray, device: torch.device, batch_size: int) -> np.ndarray:
    model.eval()
    embeddings = []
    loader = DataLoader(torch.from_numpy(X).float(), batch_size=batch_size, shuffle=False)
    with torch.no_grad():
        for X_batch in loader:
            _, z = model(X_batch.to(device))
            embeddings.append(z.cpu().numpy())
    return np.concatenate(embeddings)


def save_curve(history: list[dict[str, float]], output_path: Path) -> None:
    frame = pd.DataFrame(history)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(frame["epoch"], frame["train_rmse"], label="Train masked RMSE")
    ax.plot(frame["epoch"], frame["val_rmse"], label="Validation masked RMSE")
    ax.set_title("Masked TCN Reconstruction Training Curve")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("RMSE on masked observed values")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def save_reconstruction_examples(
    model: nn.Module,
    X: np.ndarray,
    observed: np.ndarray,
    feature_names: list[str],
    output_path: Path,
    device: torch.device,
    mask_fraction: float,
) -> None:
    sample = torch.from_numpy(X[:1]).float().to(device)
    observed_sample = torch.from_numpy(observed[:1].astype(np.float32)).to(device)
    masked, random_mask = apply_random_mask(sample, observed_sample, mask_fraction)
    model.eval()
    with torch.no_grad():
        reconstruction, _ = model(masked)

    feature_scores = random_mask[0].sum(dim=1).cpu().numpy()
    top_features = np.argsort(feature_scores)[-4:][::-1]
    days = np.arange(sample.shape[-1])

    fig, axes = plt.subplots(len(top_features), 1, figsize=(12, 2.6 * len(top_features)), sharex=True)
    if len(top_features) == 1:
        axes = [axes]
    for ax, feature_idx in zip(axes, top_features):
        ax.plot(days, sample[0, feature_idx].cpu().numpy(), label="Original standardized")
        ax.plot(days, masked[0, feature_idx].cpu().numpy(), label="Masked input", alpha=0.7)
        ax.plot(days, reconstruction[0, feature_idx].cpu().numpy(), label="Reconstruction", alpha=0.85)
        masked_days = random_mask[0, feature_idx].cpu().numpy().astype(bool)
        ax.scatter(days[masked_days], sample[0, feature_idx].cpu().numpy()[masked_days], s=18, label="Masked target")
        ax.set_ylabel(feature_names[feature_idx])
        ax.grid(alpha=0.25)
    axes[0].set_title("Masked Reconstruction Examples")
    axes[-1].set_xlabel("Day in 28-day window")
    axes[0].legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def compare_supervised_embeddings(pretrained: pd.DataFrame, output_dir: Path) -> dict[str, float | int | None]:
    supervised_path = Path("outputs/modeling/tcn/embeddings.csv")
    if not supervised_path.exists():
        return {"aligned_rows": 0, "norm_correlation": None, "distance_correlation": None}
    supervised = pd.read_csv(supervised_path)
    merged = supervised.merge(pretrained, on=["split", "date"], suffixes=("_supervised", "_pretrained"))
    sup_cols = [col for col in merged.columns if col.startswith("z_") and col.endswith("_supervised")]
    pre_cols = [col for col in merged.columns if col.startswith("z_") and col.endswith("_pretrained")]
    if not sup_cols or len(sup_cols) != len(pre_cols):
        return {"aligned_rows": int(len(merged)), "norm_correlation": None, "distance_correlation": None}
    supervised_z = merged[sup_cols].to_numpy(dtype=float)
    pretrained_z = merged[pre_cols].to_numpy(dtype=float)
    supervised_norm = np.linalg.norm(supervised_z, axis=1)
    pretrained_norm = np.linalg.norm(pretrained_z, axis=1)
    norm_corr = float(np.corrcoef(supervised_norm, pretrained_norm)[0, 1])

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(pd.to_datetime(merged["date"]), supervised_norm, label="Supervised TCN embedding norm")
    ax.plot(pd.to_datetime(merged["date"]), pretrained_norm, label="Masked-pretrained embedding norm", alpha=0.85)
    ax.set_title("Supervised vs Masked-Pretrained Embedding Norms")
    ax.set_xlabel("Date")
    ax.set_ylabel("Embedding norm")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / "embedding_norm_comparison.png", dpi=160)
    plt.close(fig)

    return {
        "aligned_rows": int(len(merged)),
        "norm_correlation": norm_corr,
        "distance_correlation": None,
    }


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


def save_embedding_state_plots(embedding_frame: pd.DataFrame, output_dir: Path) -> None:
    dates = pd.to_datetime(embedding_frame["date"])
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(dates, embedding_frame["embedding_distance"], label="Distance from rolling baseline")
    ax.plot(dates, embedding_frame["anomaly_zscore"], label="Rolling z-score", alpha=0.85)
    ax.set_title("Masked-Pretrained Embedding Anomaly Scores")
    ax.set_xlabel("Date")
    ax.set_ylabel("Score")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / "pretrained_embedding_anomaly_scores.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(dates, embedding_frame["embedding_norm"], label="Embedding norm")
    ax.plot(dates, embedding_frame["embedding_drift"], label="Day-to-day embedding drift", alpha=0.85)
    ax.set_title("Masked-Pretrained Embedding Norm And Drift")
    ax.set_xlabel("Date")
    ax.set_ylabel("Embedding magnitude")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / "pretrained_embedding_norm_drift.png", dpi=160)
    plt.close(fig)

    z_cols = [col for col in embedding_frame.columns if col.startswith("z_")]
    if len(z_cols) >= 2:
        coords = PCA(n_components=2, random_state=42).fit_transform(embedding_frame[z_cols].to_numpy(dtype=float))
        split_codes = embedding_frame["split"].map({"train": 0, "validation": 1, "test": 2}).to_numpy()
        fig, ax = plt.subplots(figsize=(7, 6))
        scatter = ax.scatter(coords[:, 0], coords[:, 1], c=split_codes, s=18, alpha=0.75)
        ax.set_title("PCA Projection Of Masked-Pretrained Latent States")
        ax.set_xlabel("PC1")
        ax.set_ylabel("PC2")
        ax.grid(alpha=0.25)
        handles, _ = scatter.legend_elements()
        ax.legend(handles, ["train", "validation", "test"], title="Split")
        fig.tight_layout()
        fig.savefig(output_dir / "pretrained_embedding_pca.png", dpi=160)
        plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pretrain TCN encoder with masked reconstruction.")
    parser.add_argument("--config", type=Path, default=Path("config/model_features.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/modeling/masked_tcn"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    set_seed(args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    config = load_config(args.config)
    tcn_config = config.get("tcn", {})
    pretrain_config = config.get("masked_pretraining", {})
    dataset = build_reconstruction_dataset(config)

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    batch_size = int(pretrain_config.get("batch_size", tcn_config.get("batch_size", 32)))
    mask_fraction = float(pretrain_config.get("mask_fraction", 0.15))
    model = TCNMaskedAutoencoder(
        input_channels=len(dataset.feature_names),
        hidden_channels=int(tcn_config.get("hidden_channels", 32)),
        embedding_dim=int(tcn_config.get("embedding_dim", 16)),
        kernel_size=int(tcn_config.get("kernel_size", 3)),
        dilations=tcn_config.get("dilations", [1, 2, 4]),
        dropout=float(tcn_config.get("dropout", 0.15)),
    ).to(device)

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=float(pretrain_config.get("learning_rate", tcn_config.get("learning_rate", 1e-3))),
        weight_decay=float(pretrain_config.get("weight_decay", tcn_config.get("weight_decay", 1e-4))),
    )
    train_loader = make_loader(dataset.X_train, dataset.observed_train, batch_size=batch_size, shuffle=True)
    val_loader = make_loader(dataset.X_val, dataset.observed_val, batch_size=batch_size, shuffle=False)

    max_epochs = int(pretrain_config.get("max_epochs", 250))
    patience = int(pretrain_config.get("early_stopping_patience", 25))
    best_val_rmse = float("inf")
    best_epoch = 0
    history = []
    checkpoint_path = args.output_dir / "masked_tcn_pretrained.pt"

    for epoch in range(1, max_epochs + 1):
        model.train()
        total_loss = 0.0
        total_positions = 0.0
        for X_batch, observed_batch in train_loader:
            X_batch = X_batch.to(device)
            observed_batch = observed_batch.to(device)
            masked_batch, masked_positions = apply_random_mask(X_batch, observed_batch, mask_fraction)
            optimizer.zero_grad()
            reconstruction, _ = model(masked_batch)
            loss, _ = masked_reconstruction_loss(reconstruction, X_batch, masked_positions.float(), mask_fraction=1.0)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            total_loss += float(loss.item()) * float(masked_positions.float().sum().item())
            total_positions += float(masked_positions.float().sum().item())

        train_mse = total_loss / max(total_positions, 1.0)
        val_metrics = evaluate(model, val_loader, device, mask_fraction)
        train_rmse = float(np.sqrt(train_mse))
        history.append({"epoch": epoch, "train_rmse": train_rmse, "val_rmse": val_metrics["rmse"]})

        if val_metrics["rmse"] < best_val_rmse:
            best_val_rmse = val_metrics["rmse"]
            best_epoch = epoch
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "encoder_state_dict": model.encoder.state_dict(),
                    "feature_names": dataset.feature_names,
                    "config": {"tcn": tcn_config, "masked_pretraining": pretrain_config},
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
    history_frame.to_csv(args.output_dir / "masked_reconstruction_history.csv", index=False)
    save_curve(history, args.output_dir / "masked_reconstruction_curve.png")
    save_reconstruction_examples(
        model,
        dataset.X_val,
        dataset.observed_val,
        dataset.feature_names,
        args.output_dir / "masked_reconstruction_examples.png",
        device,
        mask_fraction,
    )

    split_arrays = {
        "train": (dataset.X_train, dataset.dates_train),
        "validation": (dataset.X_val, dataset.dates_val),
        "test": (dataset.X_test, dataset.dates_test),
    }
    rows = []
    for split_name, (X_split, dates_split) in split_arrays.items():
        embeddings = predict_embeddings(model, X_split, device, batch_size)
        for idx, date in enumerate(pd.to_datetime(dates_split)):
            row = {"split": split_name, "date": date.date().isoformat()}
            row.update({f"z_{dim}": float(value) for dim, value in enumerate(embeddings[idx])})
            rows.append(row)
    embedding_frame = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    z_cols = [col for col in embedding_frame.columns if col.startswith("z_")]
    embedding_values = embedding_frame[z_cols].to_numpy(dtype=float)
    distances, zscores, norms = rolling_anomaly_scores(
        embedding_values,
        window=int(tcn_config.get("rolling_anomaly_window", 28)),
    )
    embedding_frame["embedding_distance"] = distances
    embedding_frame["anomaly_zscore"] = zscores
    embedding_frame["embedding_norm"] = norms
    embedding_frame["embedding_drift"] = np.r_[0.0, np.linalg.norm(np.diff(embedding_values, axis=0), axis=1)]
    embedding_frame.to_csv(args.output_dir / "pretrained_embeddings.csv", index=False)
    np.save(args.output_dir / "pretrained_embeddings.npy", embedding_values)
    embedding_frame.to_csv(args.output_dir.parent / "pretrained_embeddings.csv", index=False)
    np.save(args.output_dir.parent / "pretrained_embeddings.npy", embedding_values)
    save_embedding_state_plots(embedding_frame, args.output_dir)
    comparison = compare_supervised_embeddings(embedding_frame, args.output_dir)

    summary = {
        "device": str(device),
        "best_epoch": int(best_epoch),
        "best_val_rmse": float(best_val_rmse),
        "mask_fraction": mask_fraction,
        "checkpoint": str(checkpoint_path),
        "embeddings_csv": str(args.output_dir / "pretrained_embeddings.csv"),
        "embedding_comparison": comparison,
    }
    (args.output_dir / "masked_pretraining_metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
