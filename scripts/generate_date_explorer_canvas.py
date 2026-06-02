"""Generate interactive date explorer canvas from full monitoring history."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import pandas as pd


DISPLAY_COLUMNS = [
    ("operational_alert_tier", "tier"),
    ("operational_alert_label", "alertLabel"),
    ("monitoring_signal_agreement", "agreement"),
    ("bone_stress_risk_score", "combinedScore"),
    ("bone_stress_risk_level", "combinedLevel"),
    ("bone_stress_risk_reason", "reason"),
    ("literature_bone_stress_score", "literatureScore"),
    ("literature_bone_stress_level", "literatureLevel"),
    ("personalized_bone_stress_score", "personalizedScore"),
    ("personalized_bone_stress_level", "personalizedLevel"),
    ("accumulated_frontier_state", "frontierScore"),
    ("accumulated_frontier_level", "frontierLevel"),
    ("integrated_bone_stress_score", "integratedScore"),
    ("accumulated_bone_stress_state", "accumulatedState"),
    ("accumulated_bone_stress_level", "accumulatedLevel"),
    ("recovery_strain_score", "recoveryStrain"),
    ("running_7d_sum_m", "run7Km"),
    ("running_28d_sum_m", "run28Km"),
    ("running_distance", "runKm"),
    ("running_7d_acwr", "acwr"),
    ("running_acwr_zone", "acwrZone"),
    ("running_progression_score", "progressionScore"),
    ("foster_monotony", "fosterMonotony"),
    ("embedding_novelty_score", "embeddingNovelty"),
    ("contrastive_novelty_score", "contrastiveNovelty"),
    ("readiness_forecast_error_score", "forecastError"),
    ("readiness_absolute_forecast_error_score", "absoluteForecastError"),
    ("reference_archetype_label", "archetype"),
    ("embedding_neighbor_summary", "neighbors"),
    ("frontier_attribution_summary", "attribution"),
    ("frontier_attribution_drivers", "attributionDrivers"),
    ("counterfactual_hint", "counterfactual"),
    ("operational_recommendation", "recommendation"),
    ("risk_score", "recoveryRiskScore"),
    ("risk_level", "recoveryRiskLevel"),
    ("risk_reason", "recoveryReason"),
    ("accumulated_risk_state", "accumulatedRecoveryState"),
]

STRING_FIELDS = {
    "operational_alert_tier",
    "operational_alert_label",
    "monitoring_signal_agreement",
    "bone_stress_risk_level",
    "bone_stress_risk_reason",
    "literature_bone_stress_level",
    "personalized_bone_stress_level",
    "accumulated_frontier_level",
    "accumulated_bone_stress_level",
    "running_acwr_zone",
    "reference_archetype_label",
    "embedding_neighbor_summary",
    "frontier_attribution_summary",
    "frontier_attribution_drivers",
    "counterfactual_hint",
    "operational_recommendation",
    "risk_level",
    "risk_reason",
}


def fmt_num(value: object) -> float | int | str | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        if abs(number) >= 100:
            return round(number, 1)
        return round(number, 2)
    text = str(value).strip()
    return text or None


def km_from_meters(value: object) -> float | None:
    numeric = fmt_num(value)
    if numeric is None or not isinstance(numeric, (int, float)):
        return None
    return round(float(numeric) / 1000.0, 1)


def build_insights(row: pd.Series, period_label: str | None) -> list[str]:
    insights: list[str] = []
    run7 = km_from_meters(row.get("running_7d_sum_m")) or 0.0
    run28 = km_from_meters(row.get("running_28d_sum_m")) or 0.0
    acc = float(row.get("accumulated_bone_stress_state") or 0)
    tier = str(row.get("operational_alert_tier") or "clear")
    agreement = str(row.get("monitoring_signal_agreement") or "")
    lit = str(row.get("literature_bone_stress_level") or "")
    frontier = str(row.get("accumulated_frontier_level") or "")

    if acc >= 65 and run7 < 95:
        insights.append(
            f"Accumulated load state is elevated ({acc:.0f}) while this 7-day window is only {run7:.0f} km — "
            "strain is mostly carryover from earlier weeks, not this week's absolute volume."
        )
    if agreement == "literature_personalized_agree_frontier_differs":
        insights.append(
            "Literature and personalized tracks agree, but frontier differs — multivariate latent state is not "
            "matching the rule-based load picture."
        )
    if tier == "investigate_state":
        insights.append(
            "Investigate-state tier: frontier is elevated while objective load rules are modest. Check recovery "
            "markers and mixed-sport fatigue before adding intensity."
        )
    if frontier == "high" and lit != "high":
        insights.append("Frontier high with literature not high — learned-state strain without extreme km thresholds.")
    if run28 >= 340 and run7 < run28 / 4.5:
        insights.append(
            f"28-day running is high ({run28:.0f} km) but the latest 7-day window has eased ({run7:.0f} km)."
        )
    if period_label:
        insights.append(f"Falls inside detected load block: {period_label}.")
    if row.get("frontier_attribution_summary") and pd.notna(row.get("frontier_attribution_summary")):
        insights.append(str(row["frontier_attribution_summary"]))
    if not insights:
        reason = str(row.get("bone_stress_risk_reason") or "routine day")
        insights.append(f"No strong disagreement signals — dominant pattern: {reason.replace('_', ' ')}.")
    return insights[:5]


def period_for_date(periods: pd.DataFrame, target: pd.Timestamp) -> str | None:
    if periods.empty:
        return None
    for _, period in periods.iterrows():
        start = pd.Timestamp(period["start_date"])
        end = pd.Timestamp(period["end_date"])
        if start <= target <= end:
            return f"{start.date()} → {end.date()} ({period.get('dominant_bone_stress_reason', 'load block')})"
    return None


def row_to_day(row: pd.Series, periods: pd.DataFrame) -> dict[str, object]:
    day: dict[str, object] = {"date": pd.Timestamp(row["date"]).date().isoformat()}
    for source, target in DISPLAY_COLUMNS:
        value = row.get(source)
        if source in {"running_7d_sum_m", "running_28d_sum_m", "running_distance"}:
            day[target] = km_from_meters(value)
        elif source in STRING_FIELDS:
            day[target] = str(value) if pd.notna(value) else None
        else:
            day[target] = fmt_num(value)
    day["insights"] = build_insights(row, period_for_date(periods, pd.Timestamp(row["date"])))
    return day


def build_payload(
    bone: pd.DataFrame,
    risk: pd.DataFrame,
    periods: pd.DataFrame,
) -> dict[str, object]:
    bone = bone.sort_values("date").copy()
    bone["date"] = pd.to_datetime(bone["date"])
    risk_cols = ["date", "risk_score", "risk_level", "risk_reason", "accumulated_risk_state"]
    if not risk.empty:
        risk = risk.copy()
        risk["date"] = pd.to_datetime(risk["date"])
        merged = bone.merge(risk[risk_cols], on="date", how="left")
    else:
        merged = bone

    days = [row_to_day(row, periods) for _, row in merged.iterrows()]
    default_date = days[-1]["date"] if days else None

    anchors = [
        {"label": "Latest day", "date": default_date},
        {"label": "Spring 2024 all-agree", "date": "2024-02-09"},
        {"label": "Spring 2024 symptom window", "date": "2024-03-15"},
        {"label": "Feb–Mar 2025 ramp", "date": "2025-03-01"},
        {"label": "Peak 140+ km week sample", "date": None},
    ]
    high_run = merged[merged["running_7d_sum_m"].fillna(0) >= 140_000]
    if not high_run.empty:
        anchors[-1]["date"] = pd.Timestamp(high_run.iloc[0]["date"]).date().isoformat()

    return {
        "defaultDate": default_date,
        "dateStart": days[0]["date"] if days else None,
        "dateEnd": days[-1]["date"] if days else None,
        "dayCount": len(days),
        "anchors": [item for item in anchors if item["date"]],
        "days": days,
    }


def render_canvas(payload: dict[str, object]) -> str:
    data = json.dumps(payload, separators=(",", ":"))
    template = """import {
  Button,
  Callout,
  Card,
  CardBody,
  CardHeader,
  CollapsibleSection,
  Grid,
  H1,
  H2,
  H3,
  LineChart,
  Pill,
  Row,
  Select,
  Stack,
  Stat,
  Table,
  Text,
  TextInput,
  useCanvasState,
} from 'cursor/canvas';

const payload = __PAYLOAD__ as const;

type DayRecord = (typeof payload.days)[number];

const dayByDate = new Map<string, DayRecord>(payload.days.map((day) => [day.date, day]));

function findDay(date: string | null | undefined): DayRecord | undefined {
  if (!date) return undefined;
  return dayByDate.get(date);
}

function fmt(value: string | number | null | undefined, suffix = ''): string {
  if (value === null || value === undefined || value === '') return '—';
  return `${value}${suffix}`;
}

function levelTone(level: string | null | undefined): 'success' | 'warning' | 'danger' | 'info' | 'neutral' {
  if (!level) return 'neutral';
  if (level === 'high' || level === 'adjust_training' || level === 'investigate_state') return 'danger';
  if (level === 'moderate' || level === 'watch') return 'warning';
  if (level === 'low' || level === 'clear') return 'success';
  return 'info';
}

function scoreLevel(score: number | null | undefined): 'low' | 'moderate' | 'high' | '—' {
  if (score === null || score === undefined || Number.isNaN(Number(score))) return '—';
  if (Number(score) >= 70) return 'high';
  if (Number(score) >= 45) return 'moderate';
  return 'low';
}

function scoreRows(day: DayRecord | undefined) {
  if (!day) return [];
  return [
    ['Combined', fmt(day.combinedScore), day.combinedLevel ?? '—'],
    ['Literature', fmt(day.literatureScore), day.literatureLevel ?? '—'],
    ['Personalized', fmt(day.personalizedScore), day.personalizedLevel ?? '—'],
    ['Frontier', fmt(day.frontierScore), day.frontierLevel ?? '—'],
    ['Integrated', fmt(day.integratedScore), scoreLevel(day.integratedScore)],
    ['Recovery risk', fmt(day.recoveryRiskScore), day.recoveryRiskLevel ?? '—'],
  ];
}

function loadRows(day: DayRecord | undefined) {
  if (!day) return [];
  return [
    ['7-day run', `${fmt(day.run7Km)} km`],
    ['28-day run', `${fmt(day.run28Km)} km`],
    ['Daily run', `${fmt(day.runKm)} km`],
    ['ACWR zone', day.acwrZone ?? '—'],
    ['ACWR', fmt(day.acwr)],
    ['Progression score', fmt(day.progressionScore)],
    ['Accumulated load state', fmt(day.accumulatedState)],
    ['Accumulated recovery state', fmt(day.accumulatedRecoveryState)],
    ['Recovery strain', fmt(day.recoveryStrain)],
    ['Foster monotony', fmt(day.fosterMonotony)],
    ['Embedding novelty', fmt(day.embeddingNovelty)],
    ['Contrastive novelty', fmt(day.contrastiveNovelty)],
    ['Negative readiness surprise', fmt(day.forecastError)],
  ];
}

function contextRows(day: DayRecord | undefined) {
  if (!day) return [];
  return [
    ['Alert tier', day.alertLabel ?? day.tier ?? '—'],
    ['Agreement', (day.agreement ?? '—').replace(/_/g, ' ')],
    ['Dominant reason', (day.reason ?? '—').replace(/_/g, ' ')],
    ['Archetype', day.archetype ?? '—'],
    ['Neighbors', day.neighbors ?? '—'],
    ['Attribution', day.attribution ?? '—'],
    ['Attribution detail', day.attributionDrivers ?? '—'],
    ['Counterfactual', day.counterfactual ?? '—'],
    ['Recommendation', day.recommendation ?? '—'],
    ['Recovery reason', (day.recoveryReason ?? '—').replace(/_/g, ' ')],
  ];
}

function compareRows(left: DayRecord, right: DayRecord) {
  const metrics: Array<[string, keyof DayRecord, string]> = [
    ['Combined score', 'combinedScore', ''],
    ['Literature score', 'literatureScore', ''],
    ['Frontier score', 'frontierScore', ''],
    ['7-day km', 'run7Km', ' km'],
    ['28-day km', 'run28Km', ' km'],
    ['Accumulated load', 'accumulatedState', ''],
    ['Recovery strain', 'recoveryStrain', ''],
    ['Recovery risk', 'recoveryRiskScore', ''],
  ];
  return metrics.map(([label, key, suffix]) => {
    const a = left[key];
    const b = right[key];
    const delta =
      typeof a === 'number' && typeof b === 'number'
        ? ((b - a) >= 0 ? '+' : '') + (b - a).toFixed(1)
        : '—';
    return [label, `${fmt(a)}${suffix}`, `${fmt(b)}${suffix}`, delta];
  });
}

function DayPanel({ day, title }: { day: DayRecord | undefined; title: string }) {
  if (!day) {
    return (
      <Callout tone="warning" title={title}>
        No data for this date.
      </Callout>
    );
  }

  return (
    <Stack gap={12}>
      <Callout
        tone={levelTone(day.tier)}
        title={`${title} · ${day.alertLabel ?? day.tier ?? 'Clear'} · ${(day.agreement ?? '').replace(/_/g, ' ')}`}
      >
        {(day.reason ?? 'No dominant reason').replace(/_/g, ' ')}
      </Callout>
      <Grid columns={3} gap={12}>
        <Stat value={fmt(day.run7Km)} label="7-day run (km)" tone="info" />
        <Stat value={fmt(day.accumulatedState)} label="Accumulated load" tone={levelTone(day.accumulatedLevel)} />
        <Stat value={fmt(day.combinedScore)} label="Combined score" tone={levelTone(day.combinedLevel)} />
      </Grid>
      <Text tone="secondary" size="small">
        Accumulated load is a slow-decay running strain state: recent 7-day/28-day load, ramp rate, intensity, workouts,
        and monotony carry forward day to day, so it can remain high after this week’s mileage drops.
      </Text>
      <H3>Insights</H3>
      <Stack gap={8}>
        {day.insights.map((insight) => (
          <Text key={insight}>{insight}</Text>
        ))}
      </Stack>
      <H3>Three-track scores</H3>
      <Table headers={['Track', 'Score', 'Level']} rows={scoreRows(day)} striped />
      <H3>Load and recovery</H3>
      <Table headers={['Metric', 'Value']} rows={loadRows(day)} striped />
      <CollapsibleSection title="Context and attribution" count={contextRows(day).length}>
        <Table headers={['Field', 'Value']} rows={contextRows(day)} striped />
      </CollapsibleSection>
    </Stack>
  );
}

export default function DateExplorer() {
  const [search, setSearch] = useCanvasState('search', '');
  const [selectedDate, setSelectedDate] = useCanvasState('selectedDate', payload.defaultDate ?? '');
  const [compareDate, setCompareDate] = useCanvasState('compareDate', '');
  const [filter, setFilter] = useCanvasState<'all' | 'flagged' | 'attribution' | 'disagreement'>('filter', 'all');

  const selected = findDay(selectedDate);
  const compare = findDay(compareDate);
  const selectedIndex = payload.days.findIndex((day) => day.date === selectedDate);

  const filteredDays = payload.days.filter((day) => {
    if (filter === 'flagged' && (day.tier === 'clear' || !day.tier)) return false;
    if (filter === 'attribution' && !day.attribution) return false;
    if (filter === 'disagreement' && day.agreement !== 'literature_personalized_agree_frontier_differs') return false;
    if (!search.trim()) return true;
    const q = search.trim().toLowerCase();
    return (
      day.date.includes(q)
      || (day.reason ?? '').toLowerCase().includes(q)
      || (day.agreement ?? '').toLowerCase().includes(q)
      || (day.tier ?? '').toLowerCase().includes(q)
      || (day.attribution ?? '').toLowerCase().includes(q)
    );
  });

  const browseRows = filteredDays
    .slice(-120)
    .reverse()
    .slice(0, 40)
    .map((day) => [
      day.date,
      day.alertLabel ?? day.tier ?? '—',
      (day.agreement ?? '—').replace(/_/g, ' '),
      fmt(day.run7Km),
      fmt(day.combinedScore),
      fmt(day.accumulatedState),
    ]);

  const windowStart = Math.max(0, selectedIndex - 7);
  const trendDays = payload.days.slice(windowStart, selectedIndex + 8);
  const trendCategories = trendDays.map((day) => day.date.slice(5));
  const trendCombined = trendDays.map((day) => Number(day.combinedScore ?? 0));
  const trendAccumulated = trendDays.map((day) => Number(day.accumulatedState ?? 0));
  const trendRun7 = trendDays.map((day) => Number(day.run7Km ?? 0));

  const anchorOptions = payload.anchors.map((anchor) => ({
    value: anchor.date,
    label: `${anchor.label} (${anchor.date})`,
  }));

  return (
    <Stack gap={20}>
      <Stack gap={8}>
        <H1>Date explorer</H1>
        <Text>
          Search any day from {payload.dateStart} to {payload.dateEnd} ({payload.dayCount} days). Inspect scores,
          attribution, load, and compare two dates side by side.
        </Text>
        <Text tone="secondary" size="small">
          Source: athlete_bone_stress_scores.csv + athlete_risk_scores.csv · regenerate with generate_date_explorer_canvas.py
        </Text>
      </Stack>

      <Card>
        <CardHeader>Browse</CardHeader>
        <CardBody>
          <Stack gap={12}>
            <Row gap={8} wrap>
              <TextInput
                value={search}
                onChange={setSearch}
                placeholder="Search date (2024-03), tier, reason, attribution…"
                type="search"
                style={{ minWidth: 280, flex: 1 }}
              />
              <Select
                value={selectedDate}
                onChange={setSelectedDate}
                options={[
                  { value: selectedDate, label: `Selected: ${selectedDate}` },
                  ...filteredDays.slice(-60).reverse().map((day) => ({
                    value: day.date,
                    label: `${day.date} · ${day.alertLabel ?? day.tier ?? 'clear'} · ${fmt(day.run7Km)} km/wk`,
                  })),
                ]}
              />
              <Select
                value={compareDate}
                onChange={setCompareDate}
                options={[
                  { value: '', label: 'Compare with…' },
                  ...payload.days.slice(-120).reverse().map((day) => ({
                    value: day.date,
                    label: `${day.date} · ${fmt(day.combinedScore)} score`,
                  })),
                ]}
              />
            </Row>
            <Row gap={8} wrap>
              {(['all', 'flagged', 'attribution', 'disagreement'] as const).map((item) => (
                <Pill key={item} active={filter === item} onClick={() => setFilter(item)}>
                  {item}
                </Pill>
              ))}
              {anchorOptions.map((anchor) => (
                <Button key={anchor.value} variant="secondary" onClick={() => setSelectedDate(anchor.value)}>
                  {anchor.label}
                </Button>
              ))}
            </Row>
            <Row gap={8} wrap>
              <Button
                variant="secondary"
                disabled={selectedIndex <= 0}
                onClick={() => setSelectedDate(payload.days[Math.max(0, selectedIndex - 1)].date)}
              >
                Previous day
              </Button>
              <Button
                variant="secondary"
                disabled={selectedIndex < 0 || selectedIndex >= payload.days.length - 1}
                onClick={() => setSelectedDate(payload.days[Math.min(payload.days.length - 1, selectedIndex + 1)].date)}
              >
                Next day
              </Button>
              <Button variant="secondary" onClick={() => setCompareDate(selectedDate)}>
                Set compare = selected
              </Button>
              <Button variant="secondary" onClick={() => setCompareDate('')}>
                Clear compare
              </Button>
            </Row>
          </Stack>
        </CardBody>
      </Card>

      <Grid columns={compare ? 2 : 1} gap={16}>
        <DayPanel day={selected} title={selectedDate} />
        {compare ? <DayPanel day={compare} title={compareDate} /> : null}
      </Grid>

      {compare && selected ? (
        <Stack gap={12}>
          <H2>Compare {selectedDate} vs {compareDate}</H2>
          <Table
            headers={['Metric', selectedDate, compareDate, 'Delta']}
            rows={compareRows(selected, compare)}
            striped
          />
        </Stack>
      ) : null}

      <Stack gap={12}>
        <H2>Trend around {selectedDate}</H2>
        <Text tone="secondary" size="small">±7 days · combined score, accumulated load state, 7-day run km</Text>
        <LineChart
          categories={trendCategories}
          series={[
            { name: 'Combined score', data: trendCombined, tone: 'warning' },
            { name: 'Accumulated load', data: trendAccumulated, tone: 'danger' },
            { name: '7-day run km', data: trendRun7, tone: 'info' },
          ]}
          height={240}
        />
      </Stack>

      <Stack gap={12}>
        <H2>Matching days</H2>
        <Text tone="secondary" size="small">
          Up to 40 most recent matches for the current search/filter. Use the date dropdown to jump directly.
        </Text>
        <Table
          headers={['Date', 'Alert', 'Agreement', '7d km', 'Combined', 'Accumulated']}
          rows={browseRows}
          striped
        />
      </Stack>
    </Stack>
  );
}
"""
    return template.replace("__PAYLOAD__", data)


def replace_payload_in_existing_canvas(canvas: str, payload: dict[str, object]) -> str | None:
    """Update generated data while preserving hand-polished canvas UI."""
    marker = "type DayRecord"
    start = canvas.find("const payload = ")
    end = canvas.find(marker, start)
    if start == -1 or end == -1:
        return None
    data = json.dumps(payload, separators=(",", ":"))
    return f"{canvas[:start]}const payload = {data} as const;\n\n{canvas[end:]}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate searchable date explorer canvas.")
    parser.add_argument("--bone-scores", type=Path, default=Path("outputs/analysis/athlete_bone_stress_scores.csv"))
    parser.add_argument("--risk-scores", type=Path, default=Path("outputs/analysis/athlete_risk_scores.csv"))
    parser.add_argument("--periods", type=Path, default=Path("outputs/analysis/athlete_bone_stress_periods.csv"))
    parser.add_argument("--output-json", type=Path, default=Path("outputs/analysis/date_explorer.json"))
    parser.add_argument(
        "--canvas-dir",
        type=Path,
        default=REPO_ROOT / "canvases",
    )
    args = parser.parse_args()

    bone = pd.read_csv(args.bone_scores, parse_dates=["date"])
    risk = pd.read_csv(args.risk_scores, parse_dates=["date"]) if args.risk_scores.exists() else pd.DataFrame()
    periods = pd.read_csv(args.periods, parse_dates=["start_date", "end_date"]) if args.periods.exists() else pd.DataFrame()
    payload = build_payload(bone, risk, periods)

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    args.canvas_dir.mkdir(parents=True, exist_ok=True)
    canvas_path = args.canvas_dir / "date-explorer.canvas.tsx"
    if canvas_path.exists():
        existing = canvas_path.read_text(encoding="utf-8")
        canvas = replace_payload_in_existing_canvas(existing, payload) or render_canvas(payload)
    else:
        canvas = render_canvas(payload)
    canvas_path.write_text(canvas, encoding="utf-8")
    print(f"Wrote date explorer ({payload['dayCount']} days) to {canvas_path}")


if __name__ == "__main__":
    main()
