"""Contrastive fine-tuned TCN encoder for injury-aware latent states."""

from __future__ import annotations

from pathlib import Path

import torch
from torch import nn

from src.modeling.dataset import load_config
from src.modeling.tcn import TCNMaskedAutoencoder


class ContrastiveEncoder(nn.Module):
    """Encoder head loaded from masked pretrain, optionally contrastive-fine-tuned."""

    def __init__(
        self,
        feature_count: int,
        hidden_channels: int = 32,
        embedding_dim: int = 16,
        kernel_size: int = 3,
        dilations: list[int] | tuple[int, ...] = (1, 2, 4),
        dropout: float = 0.15,
    ) -> None:
        super().__init__()
        self.encoder = TCNMaskedAutoencoder(
            input_channels=feature_count,
            hidden_channels=hidden_channels,
            embedding_dim=embedding_dim,
            kernel_size=kernel_size,
            dilations=dilations,
            dropout=dropout,
        ).encoder

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        _, z = self.encoder(x)
        return nn.functional.normalize(z, dim=1)


def build_contrastive_encoder(config_path: Path, feature_count: int, device: torch.device) -> ContrastiveEncoder:
    config = load_config(config_path)
    tcn_config = config.get("tcn", {})
    return ContrastiveEncoder(
        feature_count=feature_count,
        hidden_channels=int(tcn_config.get("hidden_channels", 32)),
        embedding_dim=int(tcn_config.get("embedding_dim", 16)),
        kernel_size=int(tcn_config.get("kernel_size", 3)),
        dilations=tcn_config.get("dilations", [1, 2, 4]),
        dropout=float(tcn_config.get("dropout", 0.15)),
    ).to(device)


def load_contrastive_encoder(
    contrastive_checkpoint: Path,
    pretrained_checkpoint: Path,
    config_path: Path,
    device: torch.device,
) -> tuple[ContrastiveEncoder, list[str]]:
    """Load contrastive encoder weights; initialize architecture from pretrain metadata."""
    pretrain_state = torch.load(pretrained_checkpoint, map_location=device)
    feature_names = list(pretrain_state.get("feature_names", []))
    feature_count = len(feature_names) or len(load_config(config_path).get("features", []))

    model = build_contrastive_encoder(config_path, feature_count, device)
    contrastive_state = torch.load(contrastive_checkpoint, map_location=device)
    model.encoder.load_state_dict(contrastive_state["encoder_state_dict"])
    model.eval()
    return model, feature_names
