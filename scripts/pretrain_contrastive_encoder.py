"""Contrastive encoder pretraining using labeled/reference load blocks vs stable periods."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from src.modeling.contrastive import build_contrastive_encoder
from src.modeling.dataset import load_config
from src.modeling.inference import build_all_inference_windows
from src.modeling.tcn import TCNMaskedAutoencoder
from src.reference_archetypes import build_reference_archetypes, embedding_columns


def set_seed(seed: int) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)


def date_mask(dates: np.ndarray, start: str, end: str) -> np.ndarray:
    start_ts = np.datetime64(start)
    end_ts = np.datetime64(end)
    parsed = dates.astype("datetime64[D]")
    return (parsed >= start_ts) & (parsed <= end_ts)


def build_pairs(
    X: np.ndarray,
    dates: np.ndarray,
    outcome_events_path: Path,
    bone_scores: pd.DataFrame,
    embeddings: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray, list[str], list[str]]:
    positive_indices: list[int] = []
    negative_indices: list[int] = []
    positive_labels: list[str] = []
    negative_labels: list[str] = []

    payload = json.loads(outcome_events_path.read_text(encoding="utf-8"))
    for event in payload.get("events", []):
        start = str(event.get("symptom_window_start") or event.get("onset_date"))
        end = str(event.get("onset_date"))
        mask = date_mask(dates, start, end)
        positive_indices.extend(np.where(mask)[0].tolist())
        positive_labels.extend([event["id"]] * int(mask.sum()))

    for ref in payload.get("reference_periods", []):
        mask = date_mask(dates, ref["start_date"], ref["end_date"])
        positive_indices.extend(np.where(mask)[0].tolist())
        positive_labels.extend([ref["id"]] * int(mask.sum()))

    archetypes = build_reference_archetypes(embeddings, bone_scores, outcome_events_path, None)
    stable = bone_scores[
        (bone_scores["bone_stress_risk_level"] == "low")
        & (bone_scores["running_7d_sum_m"].fillna(0) > 20_000)
    ].copy()
    stable["date"] = pd.to_datetime(stable["date"])
    stable_dates = set(stable["date"].dt.date.astype(str).tolist())
    for idx, day in enumerate(dates):
        if pd.Timestamp(day).date().isoformat() in stable_dates:
            negative_indices.append(idx)
            negative_labels.append("stable_high_volume")

    if not positive_indices or not negative_indices:
        raise ValueError("Need both positive (event/reference) and negative (stable) windows for contrastive training.")

    pos_idx = np.array(positive_indices, dtype=int)
    neg_idx = np.array(negative_indices, dtype=int)
    pair_count = min(len(pos_idx), len(neg_idx), 256)
    pos_choice = np.random.choice(pos_idx, size=pair_count, replace=len(pos_idx) < pair_count)
    neg_choice = np.random.choice(neg_idx, size=pair_count, replace=len(neg_idx) < pair_count)
    anchors = X[pos_choice]
    positives = X[pos_choice]
    negatives = X[neg_choice]
    return anchors, negatives, positive_labels[:pair_count], negative_labels[:pair_count]


class ContrastiveTrainer(nn.Module):
    def __init__(self, checkpoint_path: Path, device: torch.device) -> None:
        super().__init__()
        checkpoint = torch.load(checkpoint_path, map_location=device)
        config = load_config(Path("config/model_features.json"))
        feature_count = len(checkpoint.get("feature_names", [])) or 62
        self.encoder = build_contrastive_encoder(Path("config/model_features.json"), feature_count, device).encoder
        pretrain_model = TCNMaskedAutoencoder(
            input_channels=feature_count,
            hidden_channels=int(config.get("tcn", {}).get("hidden_channels", 32)),
            embedding_dim=int(config.get("tcn", {}).get("embedding_dim", 16)),
            kernel_size=int(config.get("tcn", {}).get("kernel_size", 3)),
            dilations=config.get("tcn", {}).get("dilations", [1, 2, 4]),
            dropout=float(config.get("tcn", {}).get("dropout", 0.15)),
        ).to(device)
        pretrain_model.load_state_dict(checkpoint["model_state_dict"])
        self.encoder.load_state_dict(pretrain_model.encoder.state_dict())

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        _, z = self.encoder(x)
        return nn.functional.normalize(z, dim=1)


def contrastive_loss(anchor: torch.Tensor, negative: torch.Tensor, margin: float = 0.5) -> torch.Tensor:
    pos_dist = torch.zeros(len(anchor), device=anchor.device)
    neg_dist = torch.norm(anchor - negative, dim=1)
    return torch.relu(margin + pos_dist - neg_dist).mean()


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune encoder contrastively on reference vs stable windows.")
    parser.add_argument("--checkpoint", type=Path, default=Path("outputs/modeling/masked_tcn/masked_tcn_pretrained.pt"))
    parser.add_argument("--outcomes", type=Path, default=Path("config/outcome_events.json"))
    parser.add_argument("--scores", type=Path, default=Path("outputs/analysis/athlete_bone_stress_scores.csv"))
    parser.add_argument("--embeddings", type=Path, default=Path("outputs/modeling/pretrained_embeddings.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/modeling/contrastive_tcn"))
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    set_seed(args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    config = load_config(Path("config/model_features.json"))
    X, _, dates, _, _ = build_all_inference_windows(config)
    bone_scores = pd.read_csv(args.scores, parse_dates=["date"])
    embeddings = pd.read_csv(args.embeddings, parse_dates=["date"])

    anchors, negatives, pos_labels, neg_labels = build_pairs(
        X, dates, args.outcomes, bone_scores, embeddings
    )
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    model = ContrastiveTrainer(args.checkpoint, device).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)

    anchor_loader = DataLoader(
        TensorDataset(torch.from_numpy(anchors).float(), torch.from_numpy(negatives).float()),
        batch_size=args.batch_size,
        shuffle=True,
    )

    history = []
    for epoch in range(1, args.epochs + 1):
        model.train()
        epoch_loss = 0.0
        batches = 0
        for anchor_batch, negative_batch in anchor_loader:
            anchor_batch = anchor_batch.to(device)
            negative_batch = negative_batch.to(device)
            optimizer.zero_grad()
            anchor_z = model(anchor_batch)
            negative_z = model(negative_batch)
            loss = contrastive_loss(anchor_z, negative_z)
            loss.backward()
            optimizer.step()
            epoch_loss += float(loss.item())
            batches += 1
        history.append({"epoch": epoch, "loss": epoch_loss / max(batches, 1)})

    torch.save(
        {
            "encoder_state_dict": model.encoder.state_dict(),
            "feature_names": list(torch.load(args.checkpoint, map_location=device).get("feature_names", [])),
            "positive_examples": len(set(pos_labels)),
            "negative_examples": len(set(neg_labels)),
            "history": history,
        },
        args.output_dir / "contrastive_encoder.pt",
    )
    pd.DataFrame(history).to_csv(args.output_dir / "contrastive_history.csv", index=False)
    summary = {
        "device": str(device),
        "pairs_trained": int(len(anchors)),
        "positive_labels": sorted(set(pos_labels)),
        "negative_labels": sorted(set(neg_labels)),
        "checkpoint": str(args.output_dir / "contrastive_encoder.pt"),
        "note": "Prototype contrastive fine-tune — push reference/event windows away from stable high-volume embeddings.",
    }
    (args.output_dir / "contrastive_metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
