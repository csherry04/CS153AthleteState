"""Lightweight Temporal Convolutional Network for athlete-state modeling."""

from __future__ import annotations

import torch
from torch import nn


class Chomp1d(nn.Module):
    """Remove right-side padding so convolutions remain causal."""

    def __init__(self, chomp_size: int) -> None:
        super().__init__()
        self.chomp_size = chomp_size

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.chomp_size == 0:
            return x
        return x[:, :, :-self.chomp_size]


class TemporalBlock(nn.Module):
    """A small residual causal convolution block."""

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int,
        dilation: int,
        dropout: float,
    ) -> None:
        super().__init__()
        padding = (kernel_size - 1) * dilation
        self.net = nn.Sequential(
            nn.Conv1d(in_channels, out_channels, kernel_size, padding=padding, dilation=dilation),
            Chomp1d(padding),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Conv1d(out_channels, out_channels, kernel_size, padding=padding, dilation=dilation),
            Chomp1d(padding),
            nn.ReLU(),
            nn.Dropout(dropout),
        )
        self.downsample = nn.Conv1d(in_channels, out_channels, kernel_size=1) if in_channels != out_channels else nn.Identity()
        self.activation = nn.ReLU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.activation(self.net(x) + self.downsample(x))


class TemporalEncoder(nn.Module):
    """Shared causal TCN encoder that returns sequence features and latent state."""

    def __init__(
        self,
        input_channels: int,
        hidden_channels: int = 32,
        embedding_dim: int = 16,
        kernel_size: int = 3,
        dilations: list[int] | tuple[int, ...] = (1, 2, 4),
        dropout: float = 0.15,
    ) -> None:
        super().__init__()
        blocks = []
        channels = input_channels
        for dilation in dilations:
            blocks.append(
                TemporalBlock(
                    in_channels=channels,
                    out_channels=hidden_channels,
                    kernel_size=kernel_size,
                    dilation=int(dilation),
                    dropout=dropout,
                )
            )
            channels = hidden_channels

        self.tcn = nn.Sequential(*blocks)
        self.embedding = nn.Sequential(
            nn.Linear(hidden_channels, embedding_dim),
            nn.ReLU(),
        )
        self.hidden_channels = hidden_channels

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Return encoded sequence and final-step latent embedding.

        Args:
            x: Tensor shaped (batch, features, time).
        """
        features = self.tcn(x)
        last_step = features[:, :, -1]
        z = self.embedding(last_step)
        return features, z


class AthleteStateTCN(nn.Module):
    """Forecast next-day readiness and expose a compact latent state embedding."""

    def __init__(
        self,
        input_channels: int,
        hidden_channels: int = 32,
        embedding_dim: int = 16,
        kernel_size: int = 3,
        dilations: list[int] | tuple[int, ...] = (1, 2, 4),
        dropout: float = 0.15,
    ) -> None:
        super().__init__()
        self.encoder = TemporalEncoder(
            input_channels=input_channels,
            hidden_channels=hidden_channels,
            embedding_dim=embedding_dim,
            kernel_size=kernel_size,
            dilations=dilations,
            dropout=dropout,
        )
        self.head = nn.Linear(embedding_dim, 1)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        _, z = self.encoder(x)
        prediction = self.head(z).squeeze(-1)
        return prediction, z


class TCNMaskedAutoencoder(nn.Module):
    """Denoising reconstruction model for masked temporal pretraining."""

    def __init__(
        self,
        input_channels: int,
        hidden_channels: int = 32,
        embedding_dim: int = 16,
        kernel_size: int = 3,
        dilations: list[int] | tuple[int, ...] = (1, 2, 4),
        dropout: float = 0.15,
    ) -> None:
        super().__init__()
        self.encoder = TemporalEncoder(
            input_channels=input_channels,
            hidden_channels=hidden_channels,
            embedding_dim=embedding_dim,
            kernel_size=kernel_size,
            dilations=dilations,
            dropout=dropout,
        )
        self.reconstruction_head = nn.Conv1d(hidden_channels, input_channels, kernel_size=1)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        sequence_features, z = self.encoder(x)
        reconstruction = self.reconstruction_head(sequence_features)
        return reconstruction, z
