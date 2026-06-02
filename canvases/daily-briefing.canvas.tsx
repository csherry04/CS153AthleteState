import {
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
} from 'cursor/canvas';

const briefing = {
  "date": "2026-05-15",
  "operational_alert_tier": "watch",
  "operational_alert_label": "Watch",
  "agreement": "all_agree",
  "reason": "sustained high running volume",
  "recommendation": "Monitor closely \u2014 sustained high running volume. Sustained volume is the driver (~72 km/week). A recovery week at 50\u201360% of recent weekly km would reduce accumulated load.",
  "counterfactual": "Sustained volume is the driver (~72 km/week). A recovery week at 50\u201360% of recent weekly km would reduce accumulated load.",
  "whatif15": "If 7-day running volume were ~15% lower (61 vs 72 km/week), literature score would move 60 \u2192 60 (+0).",
  "whatif45": "If 7-day running volume were ~45% lower (39 vs 72 km/week), literature score would move 60 \u2192 60 (+0).",
  "whatifBest": "If 7-day running volume were ~15% lower (61 vs 72 km/week), literature score would move 60 \u2192 60 (+0).",
  "attribution": "Top latent-state drivers: fitness vo2MaxValue, Fatigue duration, hiking max hr, impact weighted distance m, hiking activity count.",
  "attributionDrivers": "fitness vo2MaxValue (2.650); Fatigue duration (0.615); hiking max hr (0.541); impact weighted distance m (0.439); hiking activity count (0.372)",
  "contrastiveNovelty": "2",
  "archetype": "Bone stress injury (spring 2024)",
  "neighbors": "Latent state resembles 2024-01-06, 2025-11-08, 2026-05-02.",
  "run7Km": 71.5,
  "accumulatedState": 70.1,
  "trackRows": [
    [
      "Literature",
      "60",
      "moderate"
    ],
    [
      "Personalized",
      "57",
      "moderate"
    ],
    [
      "Frontier",
      "45",
      "moderate"
    ],
    [
      "Combined",
      "58",
      "moderate"
    ]
  ],
  "weekTrend": [
    {
      "date": "2026-05-09",
      "bone": 59.64596428571428,
      "frontier": 57.56864152723814
    },
    {
      "date": "2026-05-10",
      "bone": 66.52185714285714,
      "frontier": 56.23704466437275
    },
    {
      "date": "2026-05-11",
      "bone": 63.7120226538398,
      "frontier": 38.29024903654368
    },
    {
      "date": "2026-05-12",
      "bone": 55.56516071428571,
      "frontier": 28.843431278508955
    },
    {
      "date": "2026-05-13",
      "bone": 57.316107142857135,
      "frontier": 65.27510112829032
    },
    {
      "date": "2026-05-14",
      "bone": 67.8497678178038,
      "frontier": 57.5593817425797
    },
    {
      "date": "2026-05-15",
      "bone": 58.432357064179016,
      "frontier": 45.27953819345989
    }
  ],
  "recoveryRiskLevel": "moderate",
  "recoveryReason": "accumulated insufficient rest"
} as const;

export default function DailyBriefing() {
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
    <Stack gap={20}>
      <Stack gap={8}>
        <H1>Daily briefing</H1>
        <Text>
          Operational snapshot for {briefing.date} — what the three tracks say today and what to do next.
        </Text>
        <Text tone="secondary" size="small">
          Source: athlete_bone_stress_scores.csv · regenerate with generate_daily_briefing.py
        </Text>
      </Stack>

      <Callout tone={tierTone} title={`${briefing.operational_alert_label} · ${briefing.agreement.replace(/_/g, ' ')}`}>
        {briefing.recommendation}
      </Callout>

      <Grid columns={4} gap={12}>
        <Stat value={String(briefing.run7Km)} label="7-day running (km)" tone="info" />
        <Stat value={String(briefing.accumulatedState)} label="Accumulated load state" tone="warning" />
        <Stat value={briefing.trackRows[2][1]} label="Frontier score" tone="info" />
        <Stat value={briefing.recoveryRiskLevel} label="Recovery risk" tone="info" />
      </Grid>

      <H2>Three tracks today</H2>
      <Table headers={['Track', 'Score', 'Level']} rows={briefing.trackRows} striped />

      <H2>7-day trend</H2>
      <Text tone="secondary" size="small">Combined bone-stress score and frontier strain · last 7 scored days</Text>
      <BarChart
        categories={weekCategories}
        series={[
          { name: 'Combined bone stress', data: weekBone, tone: 'warning' },
          { name: 'Frontier strain', data: weekFrontier, tone: 'info' },
        ]}
        height={220}
      />

      <H2>Frontier context</H2>
      <Table
        headers={['Signal', 'Reading']}
        rows={[
          ['Nearest archetype', briefing.archetype],
          ['Similar past days', briefing.neighbors],
          ['Contrastive novelty', briefing.contrastiveNovelty],
          ['Latent drivers', briefing.attribution],
          ['Counterfactual', briefing.counterfactual],
          ['What-if −15% volume', briefing.whatif15],
          ['What-if −45% volume', briefing.whatif45],
          ['Dominant reason', briefing.reason.replace(/_/g, ' ')],
          ['Recovery track', `${briefing.recoveryRiskLevel} · ${briefing.recoveryReason.replace(/_/g, ' ')}`],
        ]}
        striped
      />

      <CollapsibleSection title="Regenerate briefing" count={1}>
        <Text size="small"><Code>.venv/bin/python scripts/score_athlete_risk.py</Code></Text>
        <Text size="small"><Code>.venv/bin/python scripts/generate_daily_briefing.py</Code></Text>
      </CollapsibleSection>
    </Stack>
  );
}
