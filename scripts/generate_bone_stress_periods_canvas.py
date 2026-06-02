"""Generate bone-stress period canvas from detected load blocks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import pandas as pd


def build_period_payload(
    periods: pd.DataFrame,
    scores: pd.DataFrame,
    evaluation: dict | None,
) -> dict[str, object]:
    periods = periods.sort_values("peak_accumulated_bone_stress_state", ascending=False)
    score_lookup = scores.copy()
    score_lookup["date"] = pd.to_datetime(score_lookup["date"])

    rows = []
    for _, period in periods.iterrows():
        start = pd.Timestamp(period["start_date"])
        end = pd.Timestamp(period["end_date"])
        window = score_lookup[(score_lookup["date"] >= start) & (score_lookup["date"] <= end)]
        rows.append(
            {
                "start": start.date().isoformat(),
                "end": end.date().isoformat(),
                "days": int(period.get("calendar_days", 0)),
                "elevatedDays": int(period.get("elevated_days", 0)),
                "peakState": round(float(period.get("peak_accumulated_bone_stress_state", 0)), 1),
                "peakKm": round(float(period.get("peak_running_7d_km") or 0), 1),
                "level": str(period.get("period_level", "")),
                "pattern": str(period.get("dominant_bone_stress_reason", "")).replace("_", " "),
                "summary": str(period.get("period_summary", "")),
                "allAgreeDays": int((window["monitoring_signal_agreement"] == "all_agree").sum()) if not window.empty else 0,
                "frontierHighDays": int((window["accumulated_frontier_level"] == "high").sum()) if not window.empty else 0,
                "literatureHighDays": int((window["literature_bone_stress_level"] == "high").sum()) if not window.empty else 0,
            }
        )

    latest = score_lookup.sort_values("date").iloc[-1]
    latest_date = latest["date"]
    active = None
    for row in rows:
        if pd.Timestamp(row["start"]).date() <= latest_date.date() <= (pd.Timestamp(row["end"]) + pd.Timedelta(days=7)).date():
            active = row
            break

    return {
        "periodCount": len(rows),
        "activePeriod": active,
        "periods": rows[:24],
        "validationTargets": (evaluation or {}).get("targets", []),
        "interpretation": (evaluation or {}).get(
            "interpretation",
            "Periods cluster high running-load days; use agreement counts to see when all three tracks converged.",
        ),
    }


def render_canvas(payload: dict[str, object]) -> str:
    data = json.dumps(payload, indent=2)
    return f"""import {{
  Callout,
  CollapsibleSection,
  Grid,
  H1,
  H2,
  Pill,
  Stack,
  Stat,
  Table,
  Text,
}} from 'cursor/canvas';
import {{ useState }} from 'react';

const payload = {data} as const;

type LevelFilter = 'all' | 'high' | 'moderate';

export default function BoneStressPeriods() {{
  const [filter, setFilter] = useState<LevelFilter>('all');
  const filtered = payload.periods.filter((period) => filter === 'all' || period.level === filter);

  return (
    <Stack gap={{20}}>
      <Stack gap={{8}}>
        <H1>Bone-stress periods</H1>
        <Text>
          Detected running-load blocks from clustered high bone-stress days — not single-day spikes.
        </Text>
        <Text tone="secondary" size="small">
          Source: athlete_bone_stress_periods.csv · regenerate with score_athlete_risk.py then generate_bone_stress_periods_canvas.py
        </Text>
      </Stack>

      <Grid columns={{4}} gap={{12}}>
        <Stat value={{String(payload.periodCount)}} label="Periods detected" tone="info" />
        <Stat value={{payload.activePeriod ? `${{payload.activePeriod.start}} → ${{payload.activePeriod.end}}` : 'None'}} label="Active period" tone="warning" />
        <Stat value={{payload.activePeriod ? String(payload.activePeriod.peakKm) : '—'}} label="Active peak km/week" tone="warning" />
        <Stat value={{payload.activePeriod ? String(payload.activePeriod.peakState) : '—'}} label="Active peak state" tone="warning" />
      </Grid>

      {{payload.activePeriod ? (
        <Callout tone="warning" title="Currently in or just exiting a load block">
          {{payload.activePeriod.summary}}
        </Callout>
      ) : (
        <Callout tone="success" title="No active load block">Latest day is outside detected high-load periods (±7 day grace).</Callout>
      )}}

      <H2>Filter periods</H2>
      <Stack direction="row" gap={{8}} wrap>
        {{(['all', 'high', 'moderate'] as const).map((level) => (
          <Pill key={{level}} active={{filter === level}} onClick={{() => setFilter(level)}}>
            {{level}}
          </Pill>
        ))}}
      </Stack>

      <Table
        headers={{['Start', 'End', 'Days', 'Peak km', 'Peak state', 'All agree', 'Frontier high', 'Pattern']}}
        rows={{filtered.map((period) => [
          period.start,
          period.end,
          String(period.days),
          String(period.peakKm),
          String(period.peakState),
          String(period.allAgreeDays),
          String(period.frontierHighDays),
          period.pattern,
        ])}}
        striped
      />

      <CollapsibleSection title="Period summaries" count={{filtered.length}}>
        <Stack gap={{12}}>
          {{filtered.slice(0, 8).map((period) => (
            <Callout key={{`${{period.start}}-${{period.end}}`}} tone={{period.level === 'high' ? 'warning' : 'info'}} title={{`${{period.start}} → ${{period.end}} · ${{period.peakKm}} km peak week`}}>
              {{period.summary}}
            </Callout>
          ))}}
        </Stack>
      </CollapsibleSection>

      {{payload.validationTargets.length ? (
        <Stack gap={{12}}>
          <H2>Validation anchors</H2>
          <Text tone="secondary" size="small">{{payload.interpretation}}</Text>
          <Table
            headers={{['Event', 'Literature high', 'Frontier high', 'All agree']}}
            rows={{payload.validationTargets.map((target: any) => [
              target.label,
              String(target.counts?.literature_high ?? '—'),
              String(target.counts?.frontier_high ?? '—'),
              String(target.counts?.all_agree ?? '—'),
            ])}}
            striped
          />
        </Stack>
      ) : null}}
    </Stack>
  );
}}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate bone-stress periods canvas.")
    parser.add_argument("--periods", type=Path, default=Path("outputs/analysis/athlete_bone_stress_periods.csv"))
    parser.add_argument("--scores", type=Path, default=Path("outputs/analysis/athlete_bone_stress_scores.csv"))
    parser.add_argument("--evaluation", type=Path, default=Path("outputs/analysis/frontier_outcome_evaluation.json"))
    parser.add_argument("--output-json", type=Path, default=Path("outputs/analysis/bone_stress_periods_dashboard.json"))
    parser.add_argument(
        "--canvas-dir",
        type=Path,
        default=REPO_ROOT / "canvases",
    )
    args = parser.parse_args()

    periods = pd.read_csv(args.periods, parse_dates=["start_date", "end_date"]) if args.periods.exists() else pd.DataFrame()
    scores = pd.read_csv(args.scores, parse_dates=["date"]) if args.scores.exists() else pd.DataFrame()
    evaluation = json.loads(args.evaluation.read_text(encoding="utf-8")) if args.evaluation.exists() else None
    payload = build_period_payload(periods, scores, evaluation)

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    args.canvas_dir.mkdir(parents=True, exist_ok=True)
    (args.canvas_dir / "bone-stress-periods.canvas.tsx").write_text(render_canvas(payload), encoding="utf-8")
    print(f"Wrote bone-stress periods canvas ({payload['periodCount']} periods)")


if __name__ == "__main__":
    main()
