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
      "lookback_window_start": "2024-02-05",
      "lookback_window_end": "2024-03-31",
      "lookback_days": 56,
      "days_in_window": 56,
      "counts": {
        "literature_high": 36,
        "personalized_high": 26,
        "frontier_high": 9,
        "all_agree": 15,
        "mixed_signals": 1,
        "frontier_high_literature_not": 7
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
          "date": "2024-02-11",
          "lead_days": 50
        },
        "all_agree": {
          "date": "2024-02-09",
          "lead_days": 52
        },
        "mixed_signals": {
          "date": "2024-02-08",
          "lead_days": 53
        },
        "frontier_state_70": {
          "date": "2024-02-11",
          "value": 80.062625066418,
          "lead_days": 50
        },
        "integrated_score_70": {
          "date": "2024-02-11",
          "value": 70.9850662732463,
          "lead_days": 50
        }
      },
      "peak_in_window": {
        "accumulated_frontier_state": 80.062625066418,
        "literature_bone_stress_score": 85.3108300209706,
        "personalized_bone_stress_score": 85.05446428571429,
        "bone_stress_risk_score": 85.05446428571429
      },
      "pre_symptom_high_days": 25,
      "notes": "Reported bone injury after sustained running blocks in early 2024. Edit dates if your clinical timeline differs."
    }
  ],
  "interpretation": "Before Bone stress injury (spring 2024), frontier high preceded literature high by 6 days (frontier 50d, literature 56d lead). All three tracks agreed on 2024-02-09 (52 days before). Events and reference periods are for validation only \u2014 scoring never uses these dates."
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
            Counted lookback {target.lookback_window_start} → {target.lookback_window_end} · reference window {target.symptom_window_start} → {target.evaluation_end}
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
