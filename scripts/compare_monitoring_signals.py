"""Compare literature, personalized, and frontier monitoring signals."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import pandas as pd

from src.bone_stress_literature import monitoring_agreement, risk_level


def build_comparison_frame(scores: pd.DataFrame) -> pd.DataFrame:
    frame = scores.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    if "literature_bone_stress_level" not in frame.columns:
        frame["literature_bone_stress_level"] = frame["literature_bone_stress_score"].map(risk_level)
    if "personalized_bone_stress_level" not in frame.columns:
        frame["personalized_bone_stress_level"] = frame["personalized_bone_stress_score"].map(risk_level)
    frame["literature_vs_personalized_delta"] = (
        pd.to_numeric(frame["literature_bone_stress_score"], errors="coerce")
        - pd.to_numeric(frame["personalized_bone_stress_score"], errors="coerce")
    )
    frame["integrated_vs_literature_delta"] = (
        pd.to_numeric(frame.get("integrated_bone_stress_score"), errors="coerce")
        - pd.to_numeric(frame["literature_bone_stress_score"], errors="coerce")
    )
    return frame


def summarize_disagreements(frame: pd.DataFrame) -> dict[str, object]:
    has_frontier = frame["accumulated_frontier_state"].notna()
    summary = {
        "days_scored": int(len(frame)),
        "literature_high_days": int((frame["literature_bone_stress_level"] == "high").sum()),
        "personalized_high_days": int((frame["personalized_bone_stress_level"] == "high").sum()),
        "combined_high_days": int((frame["bone_stress_risk_level"] == "high").sum()),
        "frontier_coverage_days": int(has_frontier.sum()),
        "frontier_high_days": int((frame.loc[has_frontier, "accumulated_frontier_level"] == "high").sum())
        if has_frontier.any()
        else 0,
        "agreement_counts": frame["monitoring_signal_agreement"].value_counts(dropna=False).to_dict()
        if "monitoring_signal_agreement" in frame.columns
        else {},
        "literature_high_personalized_not": int(
            ((frame["literature_bone_stress_level"] == "high") & (frame["personalized_bone_stress_level"] != "high")).sum()
        ),
        "personalized_high_literature_not": int(
            ((frame["personalized_bone_stress_level"] == "high") & (frame["literature_bone_stress_level"] != "high")).sum()
        ),
        "frontier_high_literature_not": int(
            (
                has_frontier
                & (frame["accumulated_frontier_level"] == "high")
                & (frame["literature_bone_stress_level"] != "high")
            ).sum()
        )
        if has_frontier.any()
        else 0,
    }
    return summary


def write_markdown(summary: dict[str, object], disagreements: pd.DataFrame, output_path: Path) -> None:
    lines = [
        "# Monitoring Signal Comparison",
        "",
        "This report compares three parallel signals:",
        "",
        "- **Literature track:** Gabbett ACWR zones, Edwards speed bands, Foster monotony/strain [5,8,9,45]",
        "- **Personalized track:** percentile scoring vs your own running history",
        "- **Frontier track:** TCN embedding novelty, negative readiness surprise, similarity to spring 2024 reference block",
        "",
        "## Summary",
        "",
        f"- Days scored: **{summary['days_scored']}**",
        f"- Literature high days: **{summary['literature_high_days']}**",
        f"- Personalized high days: **{summary['personalized_high_days']}**",
        f"- Combined operational high days: **{summary['combined_high_days']}**",
        f"- Frontier coverage days: **{summary['frontier_coverage_days']}**",
        f"- Literature high but personalized not: **{summary['literature_high_personalized_not']}**",
        f"- Personalized high but literature not: **{summary['personalized_high_literature_not']}**",
        f"- Frontier high but literature not: **{summary['frontier_high_literature_not']}**",
        "",
        "## Agreement counts",
        "",
    ]
    for key, value in summary.get("agreement_counts", {}).items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Largest literature vs personalized disagreements", ""])
    if disagreements.empty:
        lines.append("No major disagreements found.")
    else:
        lines.append("| Date | Literature | Personalized | Frontier | Agreement | Reason |")
        lines.append("|---|---:|---:|---:|---|---|")
        for _, row in disagreements.head(20).iterrows():
            lines.append(
                f"| {row['date'].date()} | {row['literature_bone_stress_score']:.0f} | "
                f"{row['personalized_bone_stress_score']:.0f} | "
                f"{row.get('accumulated_frontier_state', float('nan')):.0f} | "
                f"{row.get('monitoring_signal_agreement', '')} | {row.get('bone_stress_risk_reason', '')} |"
            )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare literature, personalized, and frontier monitoring signals.")
    parser.add_argument("--scores", type=Path, default=Path("outputs/analysis/athlete_bone_stress_scores.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/analysis"))
    parser.add_argument("--top-n", type=int, default=30)
    args = parser.parse_args()

    scores = pd.read_csv(args.scores, parse_dates=["date"])
    comparison = build_comparison_frame(scores)
    summary = summarize_disagreements(comparison)
    disagreements = comparison[
        comparison["literature_bone_stress_level"] != comparison["personalized_bone_stress_level"]
    ].copy()
    disagreements["abs_delta"] = disagreements["literature_vs_personalized_delta"].abs()
    disagreements = disagreements.sort_values(["abs_delta", "bone_stress_risk_score"], ascending=False)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(args.output_dir / "monitoring_signal_comparison.csv", index=False)
    disagreements.head(args.top_n).to_csv(args.output_dir / "monitoring_signal_disagreements.csv", index=False)
    (args.output_dir / "monitoring_signal_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    write_markdown(summary, disagreements, args.output_dir / "monitoring_signal_comparison.md")
    print(f"Wrote monitoring comparison outputs to {args.output_dir}")


if __name__ == "__main__":
    main()
