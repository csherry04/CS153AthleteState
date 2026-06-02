import {
  Callout,
  Divider,
  H1,
  H2,
  Stack,
  Table,
  Text,
} from 'cursor/canvas';

const report = {
  "lookback_days": 56,
  "targets": [
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

export default function FrontierOutcomes() {
  return (
    <Stack gap={20}>
      <Stack gap={8}>
        <H1>Frontier validation</H1>
        <Text>
          Did literature, personalized, and frontier tracks flag load before labeled events and reference periods?
        </Text>
        <Text tone="secondary" size="small">
          Source: frontier_outcome_evaluation.json · lookback {report.lookback_days} days
        </Text>
      </Stack>
      <Callout tone="info" title="Interpretation">{report.interpretation}</Callout>
      {report.targets.map((target) => (
        <Stack key={target.id} gap={12}>
          <Divider />
          <H2>{target.label}</H2>
          <Text tone="secondary" size="small">
            Window {target.symptom_window_start} → {target.evaluation_end}
          </Text>
          <Table
            headers={['Signal', 'Count in lookback']}
            rows={Object.entries(target.counts).map(([key, value]) => [key.replace(/_/g, ' '), String(value)])}
            striped
          />
          <Table
            headers={['First alert', 'Date', 'Lead days']}
            rows={Object.entries(target.first_signals).map(([key, value]) => [
              key.replace(/_/g, ' '),
              value ? value.date : '—',
              value ? String(value.lead_days) : '—',
            ])}
            striped
          />
        </Stack>
      ))}
    </Stack>
  );
}
