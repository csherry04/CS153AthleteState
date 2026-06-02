"""Generate daily operational briefing and canvas from latest monitoring scores."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import pandas as pd


def build_briefing(scores: pd.DataFrame, risk: pd.DataFrame) -> dict[str, object]:
    scores = scores.sort_values("date")
    latest = scores.iloc[-1]
    week = scores.tail(7)
    risk_latest = risk.sort_values("date").iloc[-1] if not risk.empty else None

    run7_km = float(latest.get("running_7d_sum_m") or 0) / 1000.0
    track_rows = [
        ["Literature", f"{latest.get('literature_bone_stress_score', 0):.0f}", str(latest.get("literature_bone_stress_level", ""))],
        ["Personalized", f"{latest.get('personalized_bone_stress_score', 0):.0f}", str(latest.get("personalized_bone_stress_level", ""))],
        ["Frontier", f"{latest.get('accumulated_frontier_state', 0):.0f}" if pd.notna(latest.get("accumulated_frontier_state")) else "—", str(latest.get("accumulated_frontier_level") or "—")],
        ["Combined", f"{latest.get('bone_stress_risk_score', 0):.0f}", str(latest.get("bone_stress_risk_level", ""))],
    ]

    week_trend = [
        {
            "date": row["date"].date().isoformat(),
            "bone": float(row["bone_stress_risk_score"]),
            "frontier": float(row["accumulated_frontier_state"]) if pd.notna(row.get("accumulated_frontier_state")) else None,
        }
        for _, row in week.iterrows()
    ]

    return {
        "date": latest["date"].date().isoformat(),
        "operational_alert_tier": str(latest.get("operational_alert_tier", "clear")),
        "operational_alert_label": str(latest.get("operational_alert_label", "Clear")),
        "agreement": str(latest.get("monitoring_signal_agreement", "")),
        "reason": str(latest.get("bone_stress_risk_reason", "")),
        "recommendation": str(latest.get("operational_recommendation", "")),
        "counterfactual": str(latest.get("counterfactual_hint", "")),
        "whatif15": str(latest.get("whatif_volume_15_summary") or "—"),
        "whatif45": str(latest.get("whatif_volume_45_summary") or "—"),
        "whatifBest": str(latest.get("whatif_best_scenario_summary") or "—"),
        "attribution": str(latest.get("frontier_attribution_summary") or "—"),
        "attributionDrivers": str(latest.get("frontier_attribution_drivers") or "—"),
        "contrastiveNovelty": (
            f"{latest.get('contrastive_novelty_score'):.0f}"
            if pd.notna(latest.get("contrastive_novelty_score"))
            else "—"
        ),
        "archetype": str(latest.get("reference_archetype_label") or "—"),
        "neighbors": str(latest.get("embedding_neighbor_summary") or "—"),
        "run7Km": round(run7_km, 1),
        "accumulatedState": round(float(latest.get("accumulated_bone_stress_state") or 0), 1),
        "trackRows": track_rows,
        "weekTrend": week_trend,
        "recoveryRiskLevel": str(risk_latest.get("risk_level")) if risk_latest is not None else "—",
        "recoveryReason": str(risk_latest.get("risk_reason")) if risk_latest is not None else "—",
    }


def render_canvas(briefing: dict[str, object]) -> str:
    data = json.dumps(briefing, indent=2)
    return f"""import {{
  BarChart,
  Callout,
  Code,
  CollapsibleSection,
  Grid,
  H1,
  H2,
  Stack,
  Stat,
  Table,
  Text,
}} from 'cursor/canvas';

const briefing = {data} as const;

export default function DailyBriefing() {{
  const weekCategories = briefing.weekTrend.map((row) => row.date.slice(5));
  const weekBone = briefing.weekTrend.map((row) => row.bone);
  const weekFrontier = briefing.weekTrend.map((row) => row.frontier ?? 0);

  const tierTone =
    briefing.operational_alert_tier === 'adjust_training'
      ? 'warning'
      : briefing.operational_alert_tier === 'investigate_state'
        ? 'danger'
        : briefing.operational_alert_tier === 'watch'
          ? 'info'
          : 'success';

  return (
    <Stack gap={{20}}>
      <Stack gap={{8}}>
        <H1>Daily briefing</H1>
        <Text>
          Operational snapshot for {{briefing.date}} — what the three tracks say today and what to do next.
        </Text>
        <Text tone="secondary" size="small">
          Source: athlete_bone_stress_scores.csv · regenerate with generate_daily_briefing.py
        </Text>
      </Stack>

      <Callout tone={{tierTone}} title={{`${{briefing.operational_alert_label}} · ${{briefing.agreement.replace(/_/g, ' ')}}`}}>
        {{briefing.recommendation}}
      </Callout>

      <Grid columns={{4}} gap={{12}}>
        <Stat value={{String(briefing.run7Km)}} label="7-day running (km)" tone="info" />
        <Stat value={{String(briefing.accumulatedState)}} label="Accumulated load state" tone="warning" />
        <Stat value={{briefing.trackRows[2][1]}} label="Frontier score" tone="info" />
        <Stat value={{briefing.recoveryRiskLevel}} label="Recovery risk" tone="info" />
      </Grid>
      <Text tone="secondary" size="small">
        Accumulated load state is the running-load carryover score. It decays slowly, so recent high volume, ramp rate,
        intensity, workouts, and monotony can keep the state elevated after the latest 7-day mileage drops.
      </Text>

      <H2>Three tracks today</H2>
      <Table headers={{['Track', 'Score', 'Level']}} rows={{briefing.trackRows}} striped />

      <H2>7-day trend</H2>
      <Text tone="secondary" size="small">Combined bone-stress score and accumulated frontier state · last 7 scored days</Text>
      <BarChart
        categories={{weekCategories}}
        series={{[
          {{ name: 'Combined bone stress', data: weekBone, tone: 'warning' }},
          {{ name: 'Accumulated frontier state', data: weekFrontier, tone: 'info' }},
        ]}}
        height={{220}}
      />

      <H2>Frontier context</H2>
      <Table
        headers={{['Signal', 'Reading']}}
        rows={{[
          ['Nearest archetype', briefing.archetype],
          ['Similar past days', briefing.neighbors],
          ['Contrastive novelty', briefing.contrastiveNovelty],
          ['Latent drivers', briefing.attribution],
          ['Counterfactual', briefing.counterfactual],
          ['What-if −15% volume', briefing.whatif15],
          ['What-if −45% volume', briefing.whatif45],
          ['Dominant reason', briefing.reason.replace(/_/g, ' ')],
          ['Recovery track', `${{briefing.recoveryRiskLevel}} · ${{briefing.recoveryReason.replace(/_/g, ' ')}}`],
        ]}}
        striped
      />

      <CollapsibleSection title="Regenerate briefing" count={{1}}>
        <Text size="small"><Code>.venv/bin/python scripts/score_athlete_risk.py</Code></Text>
        <Text size="small"><Code>.venv/bin/python scripts/generate_daily_briefing.py</Code></Text>
      </CollapsibleSection>
    </Stack>
  );
}}
"""


def render_frontier_outcomes_canvas(report: dict[str, object]) -> str:
    data = json.dumps(report, indent=2)
    return f"""import {{
  Callout,
  Divider,
  H1,
  H2,
  Stack,
  Table,
  Text,
}} from 'cursor/canvas';

const report = {data} as const;

export default function FrontierOutcomes() {{
  return (
    <Stack gap={{20}}>
      <Stack gap={{8}}>
        <H1>Frontier validation</H1>
        <Text>
          Did literature, personalized, and frontier tracks flag load before labeled events and reference periods?
        </Text>
        <Text tone="secondary" size="small">
          Source: frontier_outcome_evaluation.json · lookback {{report.lookback_days}} days
        </Text>
      </Stack>
      <Callout tone="info" title="Interpretation">{{report.interpretation}}</Callout>
      {{report.targets.map((target) => (
        <Stack key={{target.id}} gap={{12}}>
          <Divider />
          <H2>{{target.label}}</H2>
          <Text tone="secondary" size="small">
            Counted lookback {{target.lookback_window_start}} → {{target.lookback_window_end}} · reference window {{target.symptom_window_start}} → {{target.evaluation_end}}
          </Text>
          <Table
            headers={{['Signal', 'Count in lookback']}}
            rows={{Object.entries(target.counts).map(([key, value]) => [key.replace(/_/g, ' '), String(value)])}}
            striped
          />
          <Table
            headers={{['First alert', 'Date', 'Lead days']}}
            rows={{Object.entries(target.first_signals).map(([key, value]) => [
              key.replace(/_/g, ' '),
              value ? value.date : '—',
              value ? String(value.lead_days) : '—',
            ])}}
            striped
          />
        </Stack>
      ))}}
    </Stack>
  );
}}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate daily briefing outputs and canvases.")
    parser.add_argument("--scores", type=Path, default=Path("outputs/analysis/athlete_bone_stress_scores.csv"))
    parser.add_argument("--risk-scores", type=Path, default=Path("outputs/analysis/athlete_risk_scores.csv"))
    parser.add_argument("--frontier-evaluation", type=Path, default=Path("outputs/analysis/frontier_outcome_evaluation.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/analysis"))
    parser.add_argument(
        "--canvas-dir",
        type=Path,
        default=REPO_ROOT / "canvases",
    )
    args = parser.parse_args()

    scores = pd.read_csv(args.scores, parse_dates=["date"])
    risk = pd.read_csv(args.risk_scores, parse_dates=["date"]) if args.risk_scores.exists() else pd.DataFrame()
    briefing = build_briefing(scores, risk)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "daily_briefing.json").write_text(json.dumps(briefing, indent=2), encoding="utf-8")

    args.canvas_dir.mkdir(parents=True, exist_ok=True)
    (args.canvas_dir / "daily-briefing.canvas.tsx").write_text(render_canvas(briefing), encoding="utf-8")

    if args.frontier_evaluation.exists():
        report = json.loads(args.frontier_evaluation.read_text(encoding="utf-8"))
        (args.canvas_dir / "frontier-outcomes.canvas.tsx").write_text(
            render_frontier_outcomes_canvas(report),
            encoding="utf-8",
        )

    print(f"Wrote daily briefing for {briefing['date']} to {args.output_dir}")


if __name__ == "__main__":
    main()
