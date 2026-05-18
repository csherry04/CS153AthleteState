"""Interpret learned athlete-state embeddings and surface anomaly days."""

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
from sklearn.decomposition import PCA


PRIMARY_COLUMNS = {
    "readiness": ["readiness_score"],
    "load": ["load_dailyTrainingLoadAcute", "activity_training_load", "readiness_acuteLoad"],
    "hrv": ["readiness_hrvWeeklyAverage"],
    "resting_hr": ["wellness_restingHeartRate", "wellness_currentDayRestingHeartRate"],
}

ACTIVITY_COLUMNS = [
    "activity_count",
    "activity_duration_seconds",
    "activity_moving_duration_seconds",
    "activity_distance_m",
    "activity_calories",
    "activity_avg_hr",
    "activity_max_hr",
    "activity_training_load",
    "activity_steps",
]


def first_available(frame: pd.DataFrame, candidates: list[str]) -> str | None:
    return next((column for column in candidates if column in frame.columns), None)


def load_joined_frame(embeddings_path: Path, daily_path: Path) -> pd.DataFrame:
    embeddings = pd.read_csv(embeddings_path, parse_dates=["date"])
    daily = pd.read_csv(daily_path, parse_dates=["date"])
    frame = embeddings.merge(daily, on="date", how="left")
    if "anomaly_zscore" not in frame.columns and "embedding_distance" not in frame.columns:
        raise ValueError("Embeddings must include anomaly_zscore or embedding_distance.")
    if "anomaly_zscore" not in frame.columns:
        frame["anomaly_zscore"] = frame["embedding_distance"]
    return frame.sort_values("date").reset_index(drop=True)


def nearest_previous_normal_days(
    frame: pd.DataFrame,
    anomaly_idx: int,
    z_cols: list[str],
    normal_z_max: float,
    neighbors: int,
) -> list[dict[str, float | str]]:
    anomaly = frame.iloc[anomaly_idx]
    previous = frame.iloc[:anomaly_idx].copy()
    previous = previous[previous["anomaly_zscore"].fillna(np.inf) <= normal_z_max]
    if previous.empty:
        return []

    anomaly_z = anomaly[z_cols].to_numpy(dtype=float)
    previous_z = previous[z_cols].to_numpy(dtype=float)
    distances = np.linalg.norm(previous_z - anomaly_z, axis=1)
    nearest = previous.assign(neighbor_distance=distances).nsmallest(neighbors, "neighbor_distance")
    rows = []
    for _, row in nearest.iterrows():
        rows.append(
            {
                "date": pd.to_datetime(row["date"]).date().isoformat(),
                "distance": float(row["neighbor_distance"]),
                "readiness": value_or_none(row.get("readiness_score")),
                "load": value_or_none(row.get("load_dailyTrainingLoadAcute")),
                "anomaly_zscore": value_or_none(row.get("anomaly_zscore")),
            }
        )
    return rows


def value_or_none(value: object) -> float | None:
    if pd.isna(value):
        return None
    return float(value)


def build_anomaly_report(
    frame: pd.DataFrame,
    top_n: int,
    neighbors: int,
    normal_z_max: float,
) -> pd.DataFrame:
    z_cols = [column for column in frame.columns if column.startswith("z_")]
    if not z_cols:
        raise ValueError("No embedding columns found. Expected columns named z_0, z_1, ...")

    ranked = frame.sort_values(["anomaly_zscore", "embedding_distance"], ascending=False).head(top_n)
    load_col = first_available(frame, PRIMARY_COLUMNS["load"])
    hrv_col = first_available(frame, PRIMARY_COLUMNS["hrv"])
    resting_hr_col = first_available(frame, PRIMARY_COLUMNS["resting_hr"])
    activity_cols = [column for column in ACTIVITY_COLUMNS if column in frame.columns]

    rows = []
    for anomaly_idx, row in ranked.iterrows():
        nearest = nearest_previous_normal_days(frame, anomaly_idx, z_cols, normal_z_max, neighbors)
        report_row = {
            "date": pd.to_datetime(row["date"]).date().isoformat(),
            "split": row.get("split"),
            "anomaly_zscore": value_or_none(row.get("anomaly_zscore")),
            "embedding_distance": value_or_none(row.get("embedding_distance")),
            "embedding_norm": value_or_none(row.get("embedding_norm")),
            "embedding_drift": value_or_none(row.get("embedding_drift")),
            "readiness": value_or_none(row.get("readiness_score")),
            "load": value_or_none(row.get(load_col)) if load_col else None,
            "hrv": value_or_none(row.get(hrv_col)) if hrv_col else None,
            "resting_hr": value_or_none(row.get(resting_hr_col)) if resting_hr_col else None,
            "nearest_previous_normal_days": json.dumps(nearest),
        }
        for column in activity_cols:
            report_row[column] = value_or_none(row.get(column))
        rows.append(report_row)
    return pd.DataFrame(rows)


def save_anomaly_load_readiness_plot(frame: pd.DataFrame, output_path: Path) -> None:
    load_col = first_available(frame, PRIMARY_COLUMNS["load"])
    readiness_col = first_available(frame, PRIMARY_COLUMNS["readiness"])
    dates = pd.to_datetime(frame["date"])

    fig, axes = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
    axes[0].plot(dates, frame["anomaly_zscore"], label="Anomaly z-score", color="tab:red")
    axes[0].set_title("Embedding Anomaly Score Over Time")
    axes[0].set_ylabel("Anomaly z-score")
    axes[0].grid(alpha=0.25)
    axes[0].legend(loc="upper left")

    if load_col:
        axes[1].plot(dates, pd.to_numeric(frame[load_col], errors="coerce"), label=load_col, color="tab:blue")
    if readiness_col:
        axes[1].plot(dates, pd.to_numeric(frame[readiness_col], errors="coerce"), label=readiness_col, color="tab:green")
    axes[1].set_title("Training Load And Readiness Context")
    axes[1].set_xlabel("Date")
    axes[1].grid(alpha=0.25)
    axes[1].legend(loc="upper left")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def save_anomaly_scatter_plot(frame: pd.DataFrame, output_path: Path) -> None:
    load_col = first_available(frame, PRIMARY_COLUMNS["load"])
    readiness_col = first_available(frame, PRIMARY_COLUMNS["readiness"])
    if not load_col and not readiness_col:
        return

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    if load_col:
        axes[0].scatter(pd.to_numeric(frame[load_col], errors="coerce"), frame["anomaly_zscore"], alpha=0.7, s=22)
        axes[0].set_xlabel(load_col)
        axes[0].set_ylabel("Anomaly z-score")
        axes[0].set_title("Anomaly vs Training Load")
        axes[0].grid(alpha=0.25)
    else:
        axes[0].axis("off")

    if readiness_col:
        axes[1].scatter(pd.to_numeric(frame[readiness_col], errors="coerce"), frame["anomaly_zscore"], alpha=0.7, s=22, color="tab:green")
        axes[1].set_xlabel(readiness_col)
        axes[1].set_ylabel("Anomaly z-score")
        axes[1].set_title("Anomaly vs Readiness")
        axes[1].grid(alpha=0.25)
    else:
        axes[1].axis("off")
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def save_pca_plots(frame: pd.DataFrame, output_dir: Path) -> None:
    z_cols = [column for column in frame.columns if column.startswith("z_")]
    if len(z_cols) < 2:
        return
    coords = PCA(n_components=2, random_state=42).fit_transform(frame[z_cols].to_numpy(dtype=float))
    plot_specs = {
        "readiness": first_available(frame, PRIMARY_COLUMNS["readiness"]),
        "load": first_available(frame, PRIMARY_COLUMNS["load"]),
        "date": "date_ordinal",
    }
    frame = frame.copy()
    frame["date_ordinal"] = pd.to_datetime(frame["date"]).map(pd.Timestamp.toordinal)

    for name, color_col in plot_specs.items():
        if color_col is None:
            continue
        colors = pd.to_numeric(frame[color_col], errors="coerce")
        fig, ax = plt.subplots(figsize=(7, 6))
        scatter = ax.scatter(coords[:, 0], coords[:, 1], c=colors, cmap="viridis", s=22, alpha=0.8)
        ax.set_title(f"Embedding PCA Colored By {name.title()}")
        ax.set_xlabel("PC1")
        ax.set_ylabel("PC2")
        ax.grid(alpha=0.25)
        colorbar = fig.colorbar(scatter, ax=ax)
        colorbar.set_label(name if name == "date" else color_col)
        fig.tight_layout()
        fig.savefig(output_dir / f"embedding_pca_by_{name}.png", dpi=160)
        plt.close(fig)


def save_summary(report: pd.DataFrame, frame: pd.DataFrame, output_path: Path) -> None:
    summary = {
        "rows_analyzed": int(len(frame)),
        "date_range": {
            "start": pd.to_datetime(frame["date"]).min().date().isoformat(),
            "end": pd.to_datetime(frame["date"]).max().date().isoformat(),
        },
        "top_anomaly_count": int(len(report)),
        "max_anomaly_zscore": value_or_none(report["anomaly_zscore"].max()) if not report.empty else None,
        "mean_anomaly_zscore": value_or_none(frame["anomaly_zscore"].mean()),
    }
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze learned athlete-state embeddings.")
    parser.add_argument("--embeddings", type=Path, default=Path("outputs/modeling/pretrained_embeddings.csv"))
    parser.add_argument("--daily-features", type=Path, default=Path("data/processed/daily_features_with_fit.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/analysis"))
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--neighbors", type=int, default=3)
    parser.add_argument("--normal-z-max", type=float, default=1.0)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    frame = load_joined_frame(args.embeddings, args.daily_features)
    report = build_anomaly_report(frame, top_n=args.top_n, neighbors=args.neighbors, normal_z_max=args.normal_z_max)
    report.to_csv(args.output_dir / "top_embedding_anomalies.csv", index=False)
    save_anomaly_load_readiness_plot(frame, args.output_dir / "anomaly_score_load_readiness.png")
    save_anomaly_scatter_plot(frame, args.output_dir / "anomaly_score_scatter_context.png")
    save_pca_plots(frame, args.output_dir)
    save_summary(report, frame, args.output_dir / "embedding_analysis_summary.json")
    print(f"Wrote analysis outputs to {args.output_dir}")


if __name__ == "__main__":
    main()
