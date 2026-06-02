"""Generate an interpretable athlete profile from monitoring outputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd


def pct(n: int, d: int) -> str:
    if d <= 0:
        return "0%"
    return f"{100 * n / d:.0f}%"


def fmt_km(meters: float | None) -> str:
    if meters is None or pd.isna(meters):
        return "—"
    value = float(meters)
    if value > 500:
        value /= 1000.0
    return f"{value:.0f} km"


def top_period_rows(periods: pd.DataFrame, limit: int = 6) -> list[dict[str, str]]:
    ranked = periods.sort_values("peak_accumulated_bone_stress_state", ascending=False).head(limit)
    rows = []
    for _, row in ranked.iterrows():
        rows.append(
            {
                "start": str(pd.Timestamp(row["start_date"]).date()),
                "end": str(pd.Timestamp(row["end_date"]).date()),
                "days": str(int(row["calendar_days"])),
                "peakKm": fmt_km(row.get("peak_running_7d_km")),
                "pattern": str(row.get("dominant_bone_stress_reason", "")),
                "summary": plain_period_summary(row),
            }
        )
    return rows


def plain_period_summary(row: pd.Series) -> str:
    reason = str(row.get("dominant_bone_stress_reason", "elevated load"))
    peak_km = fmt_km(row.get("peak_running_7d_km"))
    start = pd.Timestamp(row["start_date"]).date()
    end = pd.Timestamp(row["end_date"]).date()
    if "progression" in reason:
        return f"Running ramped quickly ({peak_km} peak week) from {start} to {end}."
    if "volume" in reason:
        return f"Sustained high weekly running ({peak_km} peak) over {int(row['calendar_days'])} days."
    if "hard running session" in reason:
        return f"Hard sessions stacked during a {peak_km} running week."
    return f"Elevated running-load block peaking at {peak_km} weekly volume."


def build_profile(
    bone: pd.DataFrame,
    risk: pd.DataFrame,
    bone_periods: pd.DataFrame,
    risk_periods: pd.DataFrame,
    daily: pd.DataFrame,
) -> dict[str, object]:
    bone = bone.copy()
    bone["date"] = pd.to_datetime(bone["date"])
    risk = risk.copy()
    risk["date"] = pd.to_datetime(risk["date"])
    daily["date"] = pd.to_datetime(daily["date"])

    run_days = int((pd.to_numeric(daily["running_distance_m"], errors="coerce").fillna(0) > 0).sum())
    cycle_days = int((pd.to_numeric(daily["cycling_distance_m"], errors="coerce").fillna(0) > 0).sum())
    median_run = float(pd.to_numeric(daily.loc[daily["running_distance_m"].fillna(0) > 0, "running_distance_m"], errors="coerce").median())

    bone_high = bone[bone["bone_stress_risk_level"] == "high"]
    reason_counts = bone_high["bone_stress_risk_reason"].value_counts()
    top_reason = reason_counts.index[0] if len(reason_counts) else "unknown"

    pers_not_lit = int(
        ((bone["personalized_bone_stress_level"] == "high") & (bone["literature_bone_stress_level"] != "high")).sum()
    )
    lit_not_pers = int(
        ((bone["literature_bone_stress_level"] == "high") & (bone["personalized_bone_stress_level"] != "high")).sum()
    )

    merged = bone.merge(
        risk[["date", "recovery_strain_score", "risk_level", "risk_reason"]],
        on="date",
        how="left",
        suffixes=("", "_risk"),
    )
    recovery_col = "recovery_strain_score_risk" if "recovery_strain_score_risk" in merged.columns else "recovery_strain_score"
    dual_stress = int(
        (
            (merged["bone_stress_risk_level"] == "high")
            & (merged["risk_level"] == "high")
            & (merged[recovery_col].fillna(0) >= 55)
        ).sum()
    )

    low_run_elevated = bone[
        (bone["running_7d_sum_m"].fillna(0) / 1000 < 40)
        & (bone["bone_stress_risk_level"].isin(["moderate", "high"]))
    ]
    big_weeks = bone[bone["running_7d_sum_m"].fillna(0) / 1000 >= 100]
    big_week_high_rate = float((big_weeks["bone_stress_risk_level"] == "high").mean()) if len(big_weeks) else 0.0

    frontier_strain_no_load = bone[
        (bone["frontier_strain_level"] == "high") & (bone["literature_bone_stress_level"] != "high")
    ]

    yearly = (
        bone.assign(year=bone["date"].dt.year)
        .groupby("year")
        .apply(lambda frame: int((frame["bone_stress_risk_level"] == "high").sum()), include_groups=False)
        .to_dict()
    )
    yearly_categories = [str(year) for year in sorted(yearly.keys())]
    yearly_values = [int(yearly[year]) for year in sorted(yearly.keys())]

    reason_labels = [str(label).replace("_", " ") for label in reason_counts.head(5).index.tolist()]
    reason_values = [int(value) for value in reason_counts.head(5).tolist()]

    strengths = [
        {
            "title": "High-volume tolerance when progression is gradual",
            "detail": (
                f"You log many 100 km+ running weeks ({len(big_weeks)} days in that band). "
                f"Only {pct(int(big_week_high_rate * len(big_weeks)), len(big_weeks))} of those days flag high load — "
                "big blocks are not automatically risky for you when the ramp is controlled."
            ),
        },
        {
            "title": "Recovery risk usually decoupled from running load",
            "detail": (
                f"Only {dual_stress} days show both high running-load and high recovery strain. "
                "Most running stress alerts are about volume patterns, not simultaneous autonomic collapse."
            ),
        },
        {
            "title": "Strong cycling complement",
            "detail": (
                f"Running dominates ({run_days} active run days vs {cycle_days} ride days in the export), "
                f"but cycling provides non-impact load. Typical run is ~{median_run/1000:.1f} km — "
                "you accumulate volume through frequency more than single monster days."
            ),
        },
    ]

    weaknesses = [
        {
            "title": "Volume progression is your main flag",
            "detail": (
                f"{int(reason_counts.get('running volume progression', 0))} high-load days were driven by progression "
                f"vs {int(reason_counts.get('sustained high running volume', 0))} by sustained volume. "
                "Steep ramps relative to your recent baseline trigger alerts more than absolute km alone."
            ),
        },
        {
            "title": "Personalized alerts exceed literature thresholds",
            "detail": (
                f"{pers_not_lit} days were high on your percentile track but not on Gabbett/Edwards/Foster rules — "
                "you are sensitive to rapid changes vs your own history even when absolute load looks modest."
            ),
        },
        {
            "title": "Multivariate strain without obvious load (frontier)",
            "detail": (
                f"{len(frontier_strain_no_load)} days had high learned-state strain while literature load was low. "
                "The model sometimes sees recovery/load decoupling that rule scores miss — worth checking sleep, HRV, and mixed sport fatigue on those days."
            ),
        },
    ]

    if len(low_run_elevated) >= 50:
        weaknesses.append(
            {
                "title": "Alerts during modest weekly running",
                "detail": (
                    f"{len(low_run_elevated)} moderate/high days occurred with <40 km/week running — often during "
                    "bike-heavy blocks or after a relative ramp. Percentile progression still fires even when absolute km is low."
                ),
            }
        )

    recommendations = [
        {
            "priority": "high",
            "action": "Cap weekly running increases to ~10–15% when returning from bike-heavy blocks",
            "why": "Progression flags dominate your alert history; Feb–Mar 2025 and similar blocks show percentile spikes without extreme absolute load.",
        },
        {
            "priority": "high",
            "action": "After 2+ consecutive high-load running days, insert a down week or cross-train day before adding km",
            "why": f"Foster monotony median on high-load days is {bone_high['foster_monotony'].median():.1f}; repeated patterns amplify strain.",
        },
        {
            "priority": "medium",
            "action": "When frontier is high but literature is low, check readiness/HRV before adding intensity",
            "why": "These are days where the TCN sees atypical multivariate state — forecast error or embedding drift — not just km.",
        },
        {
            "priority": "medium",
            "action": "Use Edwards speed bands: keep most volume below elevated band; limit high-magnitude sessions",
            "why": (
                f"Hard-session flags often coincide with elevated/high-magnitude speed bands "
                f"({int((bone['running_edwards_speed_band'] == 'high_magnitude').sum())} high-magnitude run days in history)."
            ),
        },
        {
            "priority": "low",
            "action": "Track agreement tags: investigate when all three tracks say high",
            "why": f"Only {int((bone['monitoring_signal_agreement'] == 'all_agree').sum())} all-agree days in full history — those are your strongest convergence signals.",
        },
    ]

    track_insights = [
        {
            "track": "Literature",
            "reads_as": "Objective load guardrails",
            "your_pattern": (
                f"{int((bone['literature_bone_stress_level'] == 'high').sum())} high days. "
                f"Most high-load weeks sit in ACWR sweet spot/elevated, not always danger zone — "
                "literature confirms volume exposure more than calling every week extreme."
            ),
        },
        {
            "track": "Personalized",
            "reads_as": "Your percentile baseline",
            "your_pattern": (
                f"{int((bone['personalized_bone_stress_level'] == 'high').sum())} high days — "
                f"{pers_not_lit} more than literature. You ramp harder vs yourself than absolute thresholds suggest."
            ),
        },
        {
            "track": "Frontier",
            "reads_as": "Learned multivariate strain",
            "your_pattern": (
                f"{int(bone['frontier_strain_score'].notna().sum())} scored days; "
                f"{int((bone['frontier_strain_level'] == 'high').sum())} high. "
                "Peaks when embedding novelty or readiness forecast error spike — often around labeled spring 2024 window and selected 2024–2025 dates."
            ),
        },
    ]

    spring = bone[(bone["date"] >= "2024-03-01") & (bone["date"] <= "2024-05-15")]
    spring_note = (
        f"Labeled spring 2024 window: {int((spring['bone_stress_risk_level'] == 'high').sum())} high running-load days, "
        f"mostly sustained volume ({int((spring['bone_stress_risk_reason'] == 'sustained high running volume').sum())} days). "
        "All three tracks agreed on several peak days in March — used for validation, not to tune scores."
    )

    latest = bone.sort_values("date").iloc[-1]
    latest_date = pd.Timestamp(latest["date"]).date()
    active_period: dict[str, str] | None = None
    if len(bone_periods):
        periods = bone_periods.copy()
        periods["start_date"] = pd.to_datetime(periods["start_date"])
        periods["end_date"] = pd.to_datetime(periods["end_date"])
        grace = pd.Timedelta(days=7)
        for _, period in periods.sort_values("peak_accumulated_bone_stress_state", ascending=False).iterrows():
            if period["start_date"].date() <= latest_date <= (period["end_date"] + grace).date():
                active_period = {
                    "start": str(period["start_date"].date()),
                    "end": str(period["end_date"].date()),
                    "level": str(period.get("period_level", "moderate")),
                    "summary": plain_period_summary(period),
                }
                break

    latest_operational = {
        "date": str(latest_date),
        "tier": str(latest.get("operational_alert_tier", "clear")),
        "label": str(latest.get("operational_alert_label", "Clear")),
        "recommendation": str(latest.get("operational_recommendation", "")),
        "counterfactual": str(latest.get("counterfactual_hint", "")),
        "archetype": str(latest.get("reference_archetype_label", "")),
        "neighbors": str(latest.get("embedding_neighbor_summary", "")),
        "accumulatedState": round(float(latest.get("accumulated_bone_stress_state", 0)), 1),
        "run7Km": round(float(latest.get("running_7d_sum_m", 0)) / 1000.0, 1),
    }

    risk_window_rows = top_period_rows(bone_periods, limit=6)
    recovery_top = risk_periods.sort_values("peak_accumulated_risk_state", ascending=False).head(3)
    recovery_windows = [
        {
            "start": str(pd.Timestamp(row["start_date"]).date()),
            "end": str(pd.Timestamp(row["end_date"]).date()),
            "pattern": str(row.get("dominant_risk_reason", row.get("period_summary", "recovery strain"))),
        }
        for _, row in recovery_top.iterrows()
    ]

    return {
        "snapshot": {
            "dateStart": str(bone["date"].min().date()),
            "dateEnd": str(bone["date"].max().date()),
            "totalDays": int(len(bone)),
            "runDays": run_days,
            "cycleDays": cycle_days,
            "medianRunKm": round(median_run / 1000, 1),
            "boneHighDays": int(len(bone_high)),
            "recoveryHighDays": int((risk["risk_level"] == "high").sum()),
            "bonePeriods": int(len(bone_periods)),
            "recoveryPeriods": int(len(risk_periods)),
        },
        "identity": (
            "Predominantly a high-frequency runner who uses cycling for non-impact work. "
            "Alerts are usually about how fast running volume changes, not a single hard session in isolation."
        ),
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendations": recommendations,
        "trackInsights": track_insights,
        "riskWindows": risk_window_rows,
        "recoveryWindows": recovery_windows,
        "spring2024Note": spring_note,
        "latestOperational": latest_operational,
        "activePeriod": active_period,
        "charts": {
            "highBoneDaysByYear": {"categories": yearly_categories, "values": yearly_values},
            "highDayReasons": {"labels": reason_labels, "values": reason_values},
        },
    }


def write_markdown(profile: dict[str, object], output_path: Path) -> None:
    snap = profile["snapshot"]
    lines = [
        "# Athlete profile",
        "",
        f"Data {snap['dateStart']} to {snap['dateEnd']} ({snap['totalDays']} days).",
        "",
        str(profile["identity"]),
        "",
        "## Strengths",
        "",
    ]
    for item in profile["strengths"]:
        lines.append(f"### {item['title']}")
        lines.append(str(item["detail"]))
        lines.append("")
    lines.extend(["## Risk patterns", ""])
    for item in profile["weaknesses"]:
        lines.append(f"### {item['title']}")
        lines.append(str(item["detail"]))
        lines.append("")
    lines.extend(["## When running load was riskiest", ""])
    for row in profile["riskWindows"]:
        lines.append(f"- **{row['start']} → {row['end']}** ({row['peakKm']} peak week): {row['summary']}")
    lines.extend(["", "## What to improve", ""])
    for rec in profile["recommendations"]:
        lines.append(f"- **{rec['action']}** — {rec['why']}")
    lines.extend(["", "## Spring 2024 (validation only)", "", str(profile["spring2024Note"]), ""])
    output_path.write_text("\n".join(lines), encoding="utf-8")


def render_canvas(profile: dict[str, object]) -> str:
    data_json = json.dumps(profile, indent=2)
    return f"""import {{
  BarChart,
  Callout,
  Card,
  CardBody,
  CardHeader,
  CollapsibleSection,
  Code,
  Divider,
  Grid,
  H1,
  H2,
  H3,
  Pill,
  PieChart,
  Row,
  Stack,
  Stat,
  Table,
  Text,
  useCanvasState,
}} from 'cursor/canvas';

const profile = {data_json} as const;

const sections = [
  ['overview', 'Overview'],
  ['strengths', 'Strengths'],
  ['risks', 'Risk patterns'],
  ['windows', 'Risky periods'],
  ['tracks', 'How to read scores'],
  ['actions', 'What to improve'],
] as const;

type SectionId = (typeof sections)[number][0];

function SectionNav() {{
  const [active, setActive] = useCanvasState<SectionId>('profileSection', 'overview');
  return (
    <Row gap={{8}} wrap>
      {{sections.map(([id, label]) => (
        <Pill key={{id}} active={{active === id}} onClick={{() => setActive(id)}}>
          {{label}}
        </Pill>
      ))}}
    </Row>
  );
}}

function BulletCards({{ items, tone }}: {{ items: ReadonlyArray<{{ title: string; detail: string }}>; tone: 'success' | 'warning' | 'info' }}) {{
  return (
    <Stack gap={{12}}>
      {{items.map((item) => (
        <Callout key={{item.title}} tone={{tone}} title={{item.title}}>
          {{item.detail}}
        </Callout>
      ))}}
    </Stack>
  );
}}

function ActiveSection({{ section }}: {{ section: SectionId }}) {{
  const snap = profile.snapshot;
  const charts = profile.charts;

  if (section === 'overview') {{
    return (
      <Stack gap={{16}}>
        <Callout tone="info" title="Your training fingerprint">
          {{profile.identity}}
        </Callout>
        {{profile.activePeriod ? (
          <Callout tone="warning" title={{`Active running-load period (${{profile.activePeriod.start}} → ${{profile.activePeriod.end}})`}}>
            {{profile.activePeriod.summary}} Peak accumulated state during detected blocks is tracked in the windows tab.
          </Callout>
        ) : null}}
        <Card>
          <CardHeader>Latest operational snapshot ({{profile.latestOperational.date}})</CardHeader>
          <CardBody>
            <Grid columns={{3}} gap={{12}}>
              <Stat value={{profile.latestOperational.label}} label="Alert tier" tone="warning" />
              <Stat value={{String(profile.latestOperational.run7Km)}} label="7-day run km" tone="info" />
              <Stat value={{String(profile.latestOperational.accumulatedState)}} label="Accumulated load state" tone="warning" />
            </Grid>
            <Divider />
            <Text>{{profile.latestOperational.recommendation}}</Text>
            {{profile.latestOperational.counterfactual ? (
              <Text tone="secondary" size="small">{{profile.latestOperational.counterfactual}}</Text>
            ) : null}}
            {{profile.latestOperational.archetype ? (
              <Text tone="secondary" size="small">Reference pattern: {{profile.latestOperational.archetype}}</Text>
            ) : null}}
            {{profile.latestOperational.neighbors ? (
              <Text tone="secondary" size="small">{{profile.latestOperational.neighbors}}</Text>
            ) : null}}
          </CardBody>
        </Card>
        <Grid columns={{4}} gap={{12}}>
          <Stat value={{String(snap.totalDays)}} label="Days in history" tone="info" />
          <Stat value={{String(snap.runDays)}} label="Run days" tone="info" />
          <Stat value={{String(snap.boneHighDays)}} label="High running-load days" tone="warning" />
          <Stat value={{String(snap.recoveryHighDays)}} label="High recovery-risk days" tone="warning" />
        </Grid>
        <H2>High running-load days by year</H2>
        <Text tone="secondary" size="small">Source: athlete_bone_stress_scores.csv · count of high bone_stress_risk_level days</Text>
        <BarChart
          categories={{charts.highBoneDaysByYear.categories}}
          series={{[{{ name: 'High load days', data: charts.highBoneDaysByYear.values, tone: 'warning' }}]}}
          height={{220}}
          valueSuffix=""
        />
        <H2>What triggers high-load alerts</H2>
        <Text tone="secondary" size="small">Top reasons on high bone-stress days</Text>
        <PieChart
          data={{charts.highDayReasons.labels.map((label, idx) => ({{
            label,
            value: charts.highDayReasons.values[idx],
            tone: idx === 0 ? 'warning' : 'neutral',
          }}))}}
          donut
          size={{220}}
        />
        <Text tone="secondary" size="small">{{profile.spring2024Note}}</Text>
      </Stack>
    );
  }}

  if (section === 'strengths') {{
    return (
      <Stack gap={{16}}>
        <Text>
          These are patterns where your data suggests resilience — not immunity from injury, but areas where load and
          recovery have stayed aligned more often.
        </Text>
        <BulletCards items={{profile.strengths}} tone="success" />
      </Stack>
    );
  }}

  if (section === 'risks') {{
    return (
      <Stack gap={{16}}>
        <Text>
          Recurring ways monitoring flags you — usually about ramp rate, repeated patterns, or learned-state strain
          that rules alone do not capture.
        </Text>
        <BulletCards items={{profile.weaknesses}} tone="warning" />
      </Stack>
    );
  }}

  if (section === 'windows') {{
    return (
      <Stack gap={{16}}>
        <H2>Running-load blocks</H2>
        <Text tone="secondary" size="small">Source: athlete_bone_stress_periods.csv · plain-language summaries</Text>
        <Table
          headers={{['Start', 'End', 'Peak week', 'Pattern', 'What happened']}}
          rows={{profile.riskWindows.map((row) => [row.start, row.end, row.peakKm, row.pattern, row.summary])}}
          striped
        />
        <H2>Recovery-risk blocks</H2>
        <Text tone="secondary" size="small">Source: athlete_risk_periods.csv · autonomic recovery lagging workload</Text>
        <Table
          headers={{['Start', 'End', 'Dominant pattern']}}
          rows={{profile.recoveryWindows.map((row) => [row.start, row.end, row.pattern])}}
          striped
        />
      </Stack>
    );
  }}

  if (section === 'tracks') {{
    return (
      <Stack gap={{16}}>
        <Callout tone="info" title="Three tracks, one athlete">
          Literature = defensible rules. Personalized = your percentiles. Frontier = TCN learned state. Disagreement is
          informative — not a bug.
        </Callout>
        {{profile.trackInsights.map((item) => (
          <Card key={{item.track}} variant="outline">
            <CardHeader title={{item.track}} subtitle={{item.reads_as}} />
            <CardBody>
              <Text>{{item.your_pattern}}</Text>
            </CardBody>
          </Card>
        ))}}
      </Stack>
    );
  }}

  return (
    <Stack gap={{16}}>
      <Text>Practical adjustments based on your dominant alert patterns — not generic training advice.</Text>
      {{profile.recommendations.map((rec) => (
        <Callout
          key={{rec.action}}
          tone={{rec.priority === 'high' ? 'warning' : rec.priority === 'medium' ? 'info' : 'success'}}
          title={{rec.action}}
        >
          {{rec.why}}
        </Callout>
      ))}}
      <CollapsibleSection title="Regenerate this profile" count={{1}}>
        <Text size="small">
          <Code>.venv/bin/python scripts/generate_athlete_profile.py</Code>
        </Text>
      </CollapsibleSection>
    </Stack>
  );
}}

export default function AthleteProfile() {{
  const [active] = useCanvasState<SectionId>('profileSection', 'overview');
  return (
    <Stack gap={{20}}>
      <Stack gap={{8}}>
        <H1>Athlete profile</H1>
        <Text>
          Interpretable summary of your training strengths, risk patterns, and what to adjust — derived from {{
            profile.snapshot.dateStart
          }}{' '}
          to {{profile.snapshot.dateEnd}} Garmin data.
        </Text>
        <Text tone="secondary" size="small">
          Regenerate after new exports with generate_athlete_profile.py
        </Text>
      </Stack>
      <SectionNav />
      <Divider />
      <ActiveSection section={{active}} />
    </Stack>
  );
}}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate interpretable athlete profile outputs.")
    parser.add_argument("--bone-scores", type=Path, default=Path("outputs/analysis/athlete_bone_stress_scores.csv"))
    parser.add_argument("--risk-scores", type=Path, default=Path("outputs/analysis/athlete_risk_scores.csv"))
    parser.add_argument("--bone-periods", type=Path, default=Path("outputs/analysis/athlete_bone_stress_periods.csv"))
    parser.add_argument("--risk-periods", type=Path, default=Path("outputs/analysis/athlete_risk_periods.csv"))
    parser.add_argument("--daily-features", type=Path, default=Path("data/processed/daily_features_with_fit_deduped.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/analysis"))
    parser.add_argument(
        "--canvas-path",
        type=Path,
        default=REPO_ROOT / "canvases" / "athlete-profile.canvas.tsx",
    )
    args = parser.parse_args()

    bone = pd.read_csv(args.bone_scores, parse_dates=["date"])
    risk = pd.read_csv(args.risk_scores, parse_dates=["date"])
    bone_periods = pd.read_csv(args.bone_periods, parse_dates=["start_date", "end_date"])
    risk_periods = pd.read_csv(args.risk_periods, parse_dates=["start_date", "end_date"])
    daily = pd.read_csv(args.daily_features, parse_dates=["date"], low_memory=False)

    profile = build_profile(bone, risk, bone_periods, risk_periods, daily)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "athlete_profile.json").write_text(json.dumps(profile, indent=2), encoding="utf-8")
    write_markdown(profile, args.output_dir / "athlete_profile.md")
    args.canvas_path.parent.mkdir(parents=True, exist_ok=True)
    args.canvas_path.write_text(render_canvas(profile), encoding="utf-8")
    print(f"Wrote profile to {args.output_dir} and canvas to {args.canvas_path}")


if __name__ == "__main__":
    main()
