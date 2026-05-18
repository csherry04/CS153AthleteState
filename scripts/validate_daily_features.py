"""Generate exploratory validation reports for the daily feature table."""

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
import pandas as pd

from src.modeling.dataset import load_config


def save_timeseries_plot(frame: pd.DataFrame, date_column: str, column: str, output_dir: Path) -> None:
    series = pd.to_numeric(frame[column], errors="coerce")
    if series.notna().sum() == 0:
        return

    monthly = (
        pd.DataFrame({date_column: frame[date_column], column: series})
        .set_index(date_column)
        .resample("MS")
        .mean()
    )
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(monthly.index, monthly[column], marker="o", linewidth=1.5)
    ax.set_title(f"Monthly mean: {column}")
    ax.set_xlabel("Date")
    ax.set_ylabel(column)
    ax.grid(alpha=0.25)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / f"{column}_monthly.png", dpi=160)
    plt.close(fig)


def save_missingness_plot(missingness: pd.DataFrame, output_dir: Path) -> None:
    top = missingness.sort_values("missing_pct", ascending=False).head(40)
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.barh(top["column"], top["missing_pct"])
    ax.set_title("Top 40 Columns By Missingness")
    ax.set_xlabel("Missing values (%)")
    ax.set_ylabel("Column")
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(output_dir / "missingness_top40.png", dpi=160)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate processed Garmin daily features.")
    parser.add_argument("--config", type=Path, default=Path("config/model_features.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/validation"))
    args = parser.parse_args()

    config = load_config(args.config)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    date_column = config.get("date_column", "date")
    frame = pd.read_csv(config["data_path"], parse_dates=[date_column])
    frame = frame.sort_values(date_column)

    missingness = pd.DataFrame(
        {
            "column": frame.columns,
            "missing_count": frame.isna().sum().to_numpy(),
            "missing_pct": (frame.isna().mean() * 100).round(2).to_numpy(),
            "non_null_count": frame.notna().sum().to_numpy(),
            "dtype": [str(dtype) for dtype in frame.dtypes],
        }
    ).sort_values(["missing_pct", "column"], ascending=[False, True])
    missingness.to_csv(output_dir / "missingness_report.csv", index=False)

    numeric = frame.drop(columns=[date_column]).apply(pd.to_numeric, errors="coerce")
    summary = numeric.describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95]).T
    summary["missing_pct"] = numeric.isna().mean() * 100
    summary.to_csv(output_dir / "summary_statistics.csv")

    overview = {
        "data_path": config["data_path"],
        "rows": int(len(frame)),
        "columns": int(frame.shape[1]),
        "date_min": frame[date_column].min().date().isoformat(),
        "date_max": frame[date_column].max().date().isoformat(),
        "configured_features": len(config["features"]),
        "available_configured_features": len([col for col in config["features"] if col in frame.columns]),
        "target_column": config["target_column"],
        "target_non_null_rows": int(frame[config["target_column"]].notna().sum()),
    }
    (output_dir / "overview.json").write_text(json.dumps(overview, indent=2), encoding="utf-8")

    save_missingness_plot(missingness, output_dir)
    for column in config.get("plot_columns", []):
        if column in frame.columns:
            save_timeseries_plot(frame, date_column, column, output_dir)

    print(json.dumps(overview, indent=2))
    print(f"Wrote validation reports and plots to {output_dir}")


if __name__ == "__main__":
    main()
