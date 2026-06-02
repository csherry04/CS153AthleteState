import {
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
} from 'cursor/canvas';
import { useState } from 'react';

const payload = {
  "periodCount": 48,
  "activePeriod": {
    "start": "2026-04-22",
    "end": "2026-05-08",
    "days": 17,
    "elevatedDays": 13,
    "peakState": 75.2,
    "peakKm": 108.6,
    "level": "high",
    "pattern": "sustained high running volume",
    "summary": "Sustained elevated bone-stress load from 2026-04-22 to 2026-05-08 (17 calendar days). Accumulated bone-stress state peaked at 75 with 13 high day(s). Dominant pattern: sustained high running volume. Peak 7-day running total 109 km.",
    "allAgreeDays": 4,
    "frontierHighDays": 0,
    "literatureHighDays": 3
  },
  "periods": [
    {
      "start": "2023-06-12",
      "end": "2023-07-27",
      "days": 46,
      "elevatedDays": 46,
      "peakState": 84.2,
      "peakKm": 131.0,
      "level": "high",
      "pattern": "running volume progression",
      "summary": "Sustained elevated bone-stress load from 2023-06-12 to 2023-07-27 (46 calendar days). Accumulated bone-stress state peaked at 84 with 46 high day(s). Dominant pattern: running volume progression. Peak 7-day running total 131 km.",
      "allAgreeDays": 1,
      "frontierHighDays": 1,
      "literatureHighDays": 39
    },
    {
      "start": "2023-08-05",
      "end": "2023-08-29",
      "days": 25,
      "elevatedDays": 25,
      "peakState": 81.8,
      "peakKm": 138.4,
      "level": "high",
      "pattern": "sustained high running volume",
      "summary": "Sustained elevated bone-stress load from 2023-08-05 to 2023-08-29 (25 calendar days). Accumulated bone-stress state peaked at 82 with 25 high day(s). Dominant pattern: sustained high running volume. Peak 7-day running total 138 km.",
      "allAgreeDays": 2,
      "frontierHighDays": 2,
      "literatureHighDays": 25
    },
    {
      "start": "2022-07-12",
      "end": "2022-08-23",
      "days": 43,
      "elevatedDays": 41,
      "peakState": 81.4,
      "peakKm": 106.8,
      "level": "high",
      "pattern": "running volume progression",
      "summary": "Sustained elevated bone-stress load from 2022-07-12 to 2022-08-23 (43 calendar days). Accumulated bone-stress state peaked at 81 with 41 high day(s). Dominant pattern: running volume progression. Peak 7-day running total 107 km.",
      "allAgreeDays": 2,
      "frontierHighDays": 3,
      "literatureHighDays": 31
    },
    {
      "start": "2024-03-03",
      "end": "2024-03-27",
      "days": 25,
      "elevatedDays": 25,
      "peakState": 79.3,
      "peakKm": 143.6,
      "level": "high",
      "pattern": "sustained high running volume",
      "summary": "Sustained elevated bone-stress load from 2024-03-03 to 2024-03-27 (25 calendar days). Accumulated bone-stress state peaked at 79 with 25 high day(s). Dominant pattern: sustained high running volume. Peak 7-day running total 144 km.",
      "allAgreeDays": 5,
      "frontierHighDays": 5,
      "literatureHighDays": 25
    },
    {
      "start": "2024-04-19",
      "end": "2024-04-27",
      "days": 9,
      "elevatedDays": 9,
      "peakState": 78.2,
      "peakKm": 138.8,
      "level": "high",
      "pattern": "sustained high running volume",
      "summary": "Sustained elevated bone-stress load from 2024-04-19 to 2024-04-27 (9 calendar days). Accumulated bone-stress state peaked at 78 with 9 high day(s). Dominant pattern: sustained high running volume. Peak 7-day running total 139 km.",
      "allAgreeDays": 0,
      "frontierHighDays": 0,
      "literatureHighDays": 9
    },
    {
      "start": "2024-01-16",
      "end": "2024-01-25",
      "days": 10,
      "elevatedDays": 10,
      "peakState": 76.1,
      "peakKm": 151.6,
      "level": "high",
      "pattern": "sustained high running volume",
      "summary": "Sustained elevated bone-stress load from 2024-01-16 to 2024-01-25 (10 calendar days). Accumulated bone-stress state peaked at 76 with 10 high day(s). Dominant pattern: sustained high running volume. Peak 7-day running total 152 km.",
      "allAgreeDays": 0,
      "frontierHighDays": 0,
      "literatureHighDays": 10
    },
    {
      "start": "2022-12-30",
      "end": "2023-01-10",
      "days": 12,
      "elevatedDays": 11,
      "peakState": 76.0,
      "peakKm": 113.5,
      "level": "high",
      "pattern": "sustained high running volume",
      "summary": "Sustained elevated bone-stress load from 2022-12-30 to 2023-01-10 (12 calendar days). Accumulated bone-stress state peaked at 76 with 11 high day(s). Dominant pattern: sustained high running volume. Peak 7-day running total 114 km.",
      "allAgreeDays": 1,
      "frontierHighDays": 1,
      "literatureHighDays": 7
    },
    {
      "start": "2024-02-02",
      "end": "2024-02-07",
      "days": 6,
      "elevatedDays": 6,
      "peakState": 75.7,
      "peakKm": 131.3,
      "level": "high",
      "pattern": "sustained high running volume",
      "summary": "Sustained elevated bone-stress load from 2024-02-02 to 2024-02-07 (6 calendar days). Accumulated bone-stress state peaked at 76 with 6 high day(s). Dominant pattern: sustained high running volume. Peak 7-day running total 131 km.",
      "allAgreeDays": 0,
      "frontierHighDays": 0,
      "literatureHighDays": 6
    },
    {
      "start": "2026-04-22",
      "end": "2026-05-08",
      "days": 17,
      "elevatedDays": 13,
      "peakState": 75.2,
      "peakKm": 108.6,
      "level": "high",
      "pattern": "sustained high running volume",
      "summary": "Sustained elevated bone-stress load from 2026-04-22 to 2026-05-08 (17 calendar days). Accumulated bone-stress state peaked at 75 with 13 high day(s). Dominant pattern: sustained high running volume. Peak 7-day running total 109 km.",
      "allAgreeDays": 4,
      "frontierHighDays": 0,
      "literatureHighDays": 3
    },
    {
      "start": "2023-04-25",
      "end": "2023-05-07",
      "days": 13,
      "elevatedDays": 13,
      "peakState": 75.0,
      "peakKm": 119.2,
      "level": "high",
      "pattern": "sustained high running volume",
      "summary": "Sustained elevated bone-stress load from 2023-04-25 to 2023-05-07 (13 calendar days). Accumulated bone-stress state peaked at 75 with 13 high day(s). Dominant pattern: sustained high running volume. Peak 7-day running total 119 km.",
      "allAgreeDays": 1,
      "frontierHighDays": 2,
      "literatureHighDays": 11
    },
    {
      "start": "2023-01-26",
      "end": "2023-02-08",
      "days": 14,
      "elevatedDays": 11,
      "peakState": 75.0,
      "peakKm": 121.6,
      "level": "high",
      "pattern": "sustained high running volume",
      "summary": "Sustained elevated bone-stress load from 2023-01-26 to 2023-02-08 (14 calendar days). Accumulated bone-stress state peaked at 75 with 11 high day(s). Dominant pattern: sustained high running volume. Peak 7-day running total 122 km.",
      "allAgreeDays": 0,
      "frontierHighDays": 0,
      "literatureHighDays": 6
    },
    {
      "start": "2020-03-27",
      "end": "2020-04-21",
      "days": 26,
      "elevatedDays": 20,
      "peakState": 74.9,
      "peakKm": 96.6,
      "level": "high",
      "pattern": "sustained high running volume",
      "summary": "Sustained elevated bone-stress load from 2020-03-27 to 2020-04-21 (26 calendar days). Accumulated bone-stress state peaked at 75 with 20 high day(s). Dominant pattern: sustained high running volume. Peak 7-day running total 97 km.",
      "allAgreeDays": 3,
      "frontierHighDays": 2,
      "literatureHighDays": 4
    },
    {
      "start": "2024-04-05",
      "end": "2024-04-11",
      "days": 7,
      "elevatedDays": 7,
      "peakState": 74.9,
      "peakKm": 138.3,
      "level": "high",
      "pattern": "sustained high running volume",
      "summary": "Sustained elevated bone-stress load from 2024-04-05 to 2024-04-11 (7 calendar days). Accumulated bone-stress state peaked at 75 with 7 high day(s). Dominant pattern: sustained high running volume. Peak 7-day running total 138 km.",
      "allAgreeDays": 0,
      "frontierHighDays": 0,
      "literatureHighDays": 7
    },
    {
      "start": "2023-12-11",
      "end": "2024-01-08",
      "days": 29,
      "elevatedDays": 27,
      "peakState": 74.5,
      "peakKm": 129.3,
      "level": "high",
      "pattern": "running volume progression",
      "summary": "Sustained elevated bone-stress load from 2023-12-11 to 2024-01-08 (29 calendar days). Accumulated bone-stress state peaked at 75 with 27 high day(s). Dominant pattern: running volume progression. Peak 7-day running total 129 km.",
      "allAgreeDays": 7,
      "frontierHighDays": 4,
      "literatureHighDays": 23
    },
    {
      "start": "2023-09-09",
      "end": "2023-09-19",
      "days": 11,
      "elevatedDays": 8,
      "peakState": 73.9,
      "peakKm": 139.3,
      "level": "high",
      "pattern": "sustained high running volume",
      "summary": "Sustained elevated bone-stress load from 2023-09-09 to 2023-09-19 (11 calendar days). Accumulated bone-stress state peaked at 74 with 8 high day(s). Dominant pattern: sustained high running volume. Peak 7-day running total 139 km.",
      "allAgreeDays": 2,
      "frontierHighDays": 3,
      "literatureHighDays": 10
    },
    {
      "start": "2023-02-20",
      "end": "2023-03-14",
      "days": 23,
      "elevatedDays": 15,
      "peakState": 73.8,
      "peakKm": 130.2,
      "level": "high",
      "pattern": "sustained high running volume",
      "summary": "Sustained elevated bone-stress load from 2023-02-20 to 2023-03-14 (23 calendar days). Accumulated bone-stress state peaked at 74 with 15 high day(s). Dominant pattern: sustained high running volume. Peak 7-day running total 130 km.",
      "allAgreeDays": 3,
      "frontierHighDays": 2,
      "literatureHighDays": 20
    },
    {
      "start": "2019-06-25",
      "end": "2019-07-09",
      "days": 15,
      "elevatedDays": 15,
      "peakState": 73.3,
      "peakKm": 74.5,
      "level": "high",
      "pattern": "hard running session",
      "summary": "Sustained elevated bone-stress load from 2019-06-25 to 2019-07-09 (15 calendar days). Accumulated bone-stress state peaked at 73 with 15 high day(s). Dominant pattern: hard running session. Peak 7-day running total 74 km.",
      "allAgreeDays": 0,
      "frontierHighDays": 0,
      "literatureHighDays": 1
    },
    {
      "start": "2025-02-26",
      "end": "2025-03-06",
      "days": 9,
      "elevatedDays": 8,
      "peakState": 73.0,
      "peakKm": 67.7,
      "level": "high",
      "pattern": "running volume progression",
      "summary": "Sustained elevated bone-stress load from 2025-02-26 to 2025-03-06 (9 calendar days). Accumulated bone-stress state peaked at 73 with 8 high day(s). Dominant pattern: running volume progression. Peak 7-day running total 68 km.",
      "allAgreeDays": 1,
      "frontierHighDays": 0,
      "literatureHighDays": 0
    },
    {
      "start": "2020-11-11",
      "end": "2020-11-24",
      "days": 14,
      "elevatedDays": 12,
      "peakState": 72.8,
      "peakKm": 78.6,
      "level": "high",
      "pattern": "hard running session",
      "summary": "Sustained elevated bone-stress load from 2020-11-11 to 2020-11-24 (14 calendar days). Accumulated bone-stress state peaked at 73 with 12 high day(s). Dominant pattern: hard running session. Peak 7-day running total 79 km.",
      "allAgreeDays": 0,
      "frontierHighDays": 0,
      "literatureHighDays": 0
    },
    {
      "start": "2021-02-04",
      "end": "2021-02-13",
      "days": 10,
      "elevatedDays": 7,
      "peakState": 72.5,
      "peakKm": 81.2,
      "level": "high",
      "pattern": "hard running session",
      "summary": "Sustained elevated bone-stress load from 2021-02-04 to 2021-02-13 (10 calendar days). Accumulated bone-stress state peaked at 72 with 7 high day(s). Dominant pattern: hard running session. Peak 7-day running total 81 km.",
      "allAgreeDays": 0,
      "frontierHighDays": 0,
      "literatureHighDays": 1
    },
    {
      "start": "2019-08-06",
      "end": "2019-08-19",
      "days": 14,
      "elevatedDays": 13,
      "peakState": 72.4,
      "peakKm": 90.0,
      "level": "high",
      "pattern": "sustained high running volume",
      "summary": "Sustained elevated bone-stress load from 2019-08-06 to 2019-08-19 (14 calendar days). Accumulated bone-stress state peaked at 72 with 13 high day(s). Dominant pattern: sustained high running volume. Peak 7-day running total 90 km.",
      "allAgreeDays": 0,
      "frontierHighDays": 1,
      "literatureHighDays": 1
    },
    {
      "start": "2020-05-15",
      "end": "2020-05-29",
      "days": 15,
      "elevatedDays": 11,
      "peakState": 72.4,
      "peakKm": 92.5,
      "level": "high",
      "pattern": "sustained high running volume",
      "summary": "Sustained elevated bone-stress load from 2020-05-15 to 2020-05-29 (15 calendar days). Accumulated bone-stress state peaked at 72 with 11 high day(s). Dominant pattern: sustained high running volume. Peak 7-day running total 92 km.",
      "allAgreeDays": 0,
      "frontierHighDays": 0,
      "literatureHighDays": 0
    },
    {
      "start": "2022-05-27",
      "end": "2022-06-02",
      "days": 7,
      "elevatedDays": 5,
      "peakState": 72.4,
      "peakKm": 91.3,
      "level": "high",
      "pattern": "hard running session",
      "summary": "Sustained elevated bone-stress load from 2022-05-27 to 2022-06-02 (7 calendar days). Accumulated bone-stress state peaked at 72 with 5 high day(s). Dominant pattern: hard running session. Peak 7-day running total 91 km.",
      "allAgreeDays": 1,
      "frontierHighDays": 1,
      "literatureHighDays": 1
    },
    {
      "start": "2023-03-24",
      "end": "2023-04-11",
      "days": 19,
      "elevatedDays": 15,
      "peakState": 72.4,
      "peakKm": 122.4,
      "level": "high",
      "pattern": "sustained high running volume",
      "summary": "Sustained elevated bone-stress load from 2023-03-24 to 2023-04-11 (19 calendar days). Accumulated bone-stress state peaked at 72 with 15 high day(s). Dominant pattern: sustained high running volume. Peak 7-day running total 122 km.",
      "allAgreeDays": 0,
      "frontierHighDays": 2,
      "literatureHighDays": 14
    }
  ],
  "validationTargets": [
    {
      "id": "spring_2024_bone_stress",
      "label": "Bone stress injury (spring 2024)",
      "evaluation_end": "2024-04-01",
      "symptom_window_start": "2024-03-01",
      "lookback_days": 56,
      "days_in_window": 56,
      "counts": {
        "literature_high": 36,
        "personalized_high": 26,
        "frontier_high": 8,
        "all_agree": 9,
        "mixed_signals": 8,
        "frontier_high_literature_not": 3
      },
      "first_signals": {
        "literature_high": {
          "date": "2024-02-05",
          "lead_days": 56
        },
        "personalized_high": {
          "date": "2024-02-05",
          "lead_days": 56
        },
        "frontier_high": {
          "date": "2024-02-09",
          "lead_days": 52
        },
        "all_agree": {
          "date": "2024-02-10",
          "lead_days": 51
        },
        "mixed_signals": {
          "date": "2024-02-08",
          "lead_days": 53
        },
        "frontier_score_70": {
          "date": "2024-02-09",
          "value": 79.82129318808595,
          "lead_days": 52
        },
        "integrated_score_70": {
          "date": "2024-02-11",
          "value": 73.44634919664014,
          "lead_days": 50
        }
      },
      "peak_in_window": {
        "frontier_strain_score": 87.09486199040036,
        "literature_bone_stress_score": 85.3108300209706,
        "personalized_bone_stress_score": 85.05446428571429,
        "bone_stress_risk_score": 85.05446428571429
      },
      "pre_symptom_high_days": 25,
      "notes": "Reported bone injury after sustained running blocks in early 2024. Edit dates if your clinical timeline differs."
    },
    {
      "id": "feb_mar_2025_ramp",
      "label": "Feb\u2013Mar 2025 bike-heavy running ramp",
      "evaluation_end": "2025-03-08",
      "symptom_window_start": "2025-02-24",
      "lookback_days": 56,
      "days_in_window": 56,
      "counts": {
        "literature_high": 0,
        "personalized_high": 13,
        "frontier_high": 2,
        "all_agree": 8,
        "mixed_signals": 10,
        "frontier_high_literature_not": 2
      },
      "first_signals": {
        "literature_high": null,
        "personalized_high": {
          "date": "2025-02-05",
          "lead_days": 31
        },
        "frontier_high": {
          "date": "2025-01-11",
          "lead_days": 56
        },
        "all_agree": {
          "date": "2025-01-12",
          "lead_days": 55
        },
        "mixed_signals": {
          "date": "2025-02-05",
          "lead_days": 31
        },
        "frontier_score_70": {
          "date": "2025-01-11",
          "value": 74.19825634181365,
          "lead_days": 56
        },
        "integrated_score_70": {
          "date": "2025-01-11",
          "value": 77.92063971963478,
          "lead_days": 56
        }
      },
      "peak_in_window": {
        "frontier_strain_score": 74.19825634181365,
        "literature_bone_stress_score": 67.85000000000001,
        "personalized_bone_stress_score": 77.75471428571427,
        "bone_stress_risk_score": 79.925
      },
      "pre_symptom_high_days": 8,
      "notes": "Pseudo-prospective reference \u2014 steep running progression during bike-heavy block, not a labeled injury."
    }
  ],
  "interpretation": "Before Bone stress injury (spring 2024), frontier high preceded literature high by 4 days (frontier 52d, literature 56d lead). All three tracks agreed on 2024-02-10 (51 days before). Before Feb\u2013Mar 2025 bike-heavy running ramp, frontier flagged high with 56 days lead. All three tracks agreed on 2025-01-12 (55 days before). Events and reference periods are for validation only \u2014 scoring never uses these dates."
} as const;

type LevelFilter = 'all' | 'high' | 'moderate';

export default function BoneStressPeriods() {
  const [filter, setFilter] = useState<LevelFilter>('all');
  const filtered = payload.periods.filter((period) => filter === 'all' || period.level === filter);

  return (
    <Stack gap={20}>
      <Stack gap={8}>
        <H1>Bone-stress periods</H1>
        <Text>
          Detected running-load blocks from clustered high bone-stress days — not single-day spikes.
        </Text>
        <Text tone="secondary" size="small">
          Source: athlete_bone_stress_periods.csv · regenerate with score_athlete_risk.py then generate_bone_stress_periods_canvas.py
        </Text>
      </Stack>

      <Grid columns={4} gap={12}>
        <Stat value={String(payload.periodCount)} label="Periods detected" tone="info" />
        <Stat value={payload.activePeriod ? `${payload.activePeriod.start} → ${payload.activePeriod.end}` : 'None'} label="Active period" tone="warning" />
        <Stat value={payload.activePeriod ? String(payload.activePeriod.peakKm) : '—'} label="Active peak km/week" tone="warning" />
        <Stat value={payload.activePeriod ? String(payload.activePeriod.peakState) : '—'} label="Active peak state" tone="warning" />
      </Grid>

      {payload.activePeriod ? (
        <Callout tone="warning" title="Currently in or just exiting a load block">
          {payload.activePeriod.summary}
        </Callout>
      ) : (
        <Callout tone="success" title="No active load block">Latest day is outside detected high-load periods (±7 day grace).</Callout>
      )}

      <H2>Filter periods</H2>
      <Stack direction="row" gap={8} wrap>
        {(['all', 'high', 'moderate'] as const).map((level) => (
          <Pill key={level} active={filter === level} onClick={() => setFilter(level)}>
            {level}
          </Pill>
        ))}
      </Stack>

      <Table
        headers={['Start', 'End', 'Days', 'Peak km', 'Peak state', 'All agree', 'Frontier high', 'Pattern']}
        rows={filtered.map((period) => [
          period.start,
          period.end,
          String(period.days),
          String(period.peakKm),
          String(period.peakState),
          String(period.allAgreeDays),
          String(period.frontierHighDays),
          period.pattern,
        ])}
        striped
      />

      <CollapsibleSection title="Period summaries" count={filtered.length}>
        <Stack gap={12}>
          {filtered.slice(0, 8).map((period) => (
            <Callout key={`${period.start}-${period.end}`} tone={period.level === 'high' ? 'warning' : 'info'} title={`${period.start} → ${period.end} · ${period.peakKm} km peak week`}>
              {period.summary}
            </Callout>
          ))}
        </Stack>
      </CollapsibleSection>

      {payload.validationTargets.length ? (
        <Stack gap={12}>
          <H2>Validation anchors</H2>
          <Text tone="secondary" size="small">{payload.interpretation}</Text>
          <Table
            headers={['Event', 'Literature high', 'Frontier high', 'All agree']}
            rows={payload.validationTargets.map((target: any) => [
              target.label,
              String(target.counts?.literature_high ?? '—'),
              String(target.counts?.frontier_high ?? '—'),
              String(target.counts?.all_agree ?? '—'),
            ])}
            striped
          />
        </Stack>
      ) : null}
    </Stack>
  );
}
