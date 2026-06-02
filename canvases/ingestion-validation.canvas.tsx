import {
  BarChart,
  Callout,
  Divider,
  Grid,
  H1,
  H2,
  H3,
  LineChart,
  Stack,
  Stat,
  Table,
  Text,
} from 'cursor/canvas';

const overview = {
  rows: 2820,
  columns: 221,
  start: '2018-08-26',
  end: '2026-05-15',
  activityDays: 2169,
  totalActivities: 3232,
};

const groupCoverage = [
  { group: 'wellness', columns: 82, days: 2818, coveragePct: 99.9 },
  { group: 'training_history', columns: 11, days: 2713, coveragePct: 96.2 },
  { group: 'activity', columns: 18, days: 2169, coveragePct: 76.9 },
  { group: 'sleep', columns: 18, days: 1914, coveragePct: 67.9 },
  { group: 'fitness', columns: 11, days: 1844, coveragePct: 65.4 },
  { group: 'load', columns: 8, days: 901, coveragePct: 32.0 },
  { group: 'endurance', columns: 6, days: 901, coveragePct: 32.0 },
  { group: 'hill', columns: 8, days: 901, coveragePct: 32.0 },
  { group: 'race_prediction', columns: 6, days: 901, coveragePct: 32.0 },
  { group: 'readiness', columns: 26, days: 872, coveragePct: 30.9 },
  { group: 'acclimation', columns: 17, days: 872, coveragePct: 30.9 },
  { group: 'hydration', columns: 5, days: 617, coveragePct: 21.9 },
  { group: 'health_status', columns: 4, days: 11, coveragePct: 0.4 },
];

const annual = [
  { year: '2018', activity_count: 106 },
  { year: '2019', activity_count: 349 },
  { year: '2020', activity_count: 462 },
  { year: '2021', activity_count: 505 },
  { year: '2022', activity_count: 473 },
  { year: '2023', activity_count: 500 },
  { year: '2024', activity_count: 322 },
  { year: '2025', activity_count: 335 },
  { year: '2026', activity_count: 180 },
];

const recentMonthly = [
  { month: '2024-06', activity_count: 15 },
  { month: '2024-07', activity_count: 20 },
  { month: '2024-08', activity_count: 19 },
  { month: '2024-09', activity_count: 20 },
  { month: '2024-10', activity_count: 20 },
  { month: '2024-11', activity_count: 12 },
  { month: '2024-12', activity_count: 14 },
  { month: '2025-01', activity_count: 28 },
  { month: '2025-02', activity_count: 31 },
  { month: '2025-03', activity_count: 28 },
  { month: '2025-04', activity_count: 35 },
  { month: '2025-05', activity_count: 26 },
  { month: '2025-06', activity_count: 19 },
  { month: '2025-07', activity_count: 28 },
  { month: '2025-08', activity_count: 13 },
  { month: '2025-09', activity_count: 29 },
  { month: '2025-10', activity_count: 40 },
  { month: '2025-11', activity_count: 35 },
  { month: '2025-12', activity_count: 23 },
  { month: '2026-01', activity_count: 39 },
  { month: '2026-02', activity_count: 28 },
  { month: '2026-03', activity_count: 42 },
  { month: '2026-04', activity_count: 47 },
  { month: '2026-05', activity_count: 24 },
];

const monthlyMetrics = [
  { month: '2024-03', readiness: 59.9, load: 774.2 },
  { month: '2024-04', readiness: 68.8, load: 792.4 },
  { month: '2024-05', readiness: 86.2, load: 321.3 },
  { month: '2024-06', readiness: 64.0, load: 596.7 },
  { month: '2024-07', readiness: 68.2, load: 728.2 },
  { month: '2024-08', readiness: 62.7, load: 422.0 },
  { month: '2024-09', readiness: 58.9, load: 668.7 },
  { month: '2024-10', readiness: 64.7, load: 661.2 },
  { month: '2024-11', readiness: 61.1, load: 684.2 },
  { month: '2024-12', readiness: 65.0, load: 446.9 },
  { month: '2025-01', readiness: 50.9, load: 840.1 },
  { month: '2025-02', readiness: 63.0, load: 825.4 },
  { month: '2025-03', readiness: 46.4, load: 966.7 },
  { month: '2025-04', readiness: 55.9, load: 842.6 },
  { month: '2025-05', readiness: 60.1, load: 777.3 },
  { month: '2025-06', readiness: 67.7, load: 441.4 },
  { month: '2025-07', readiness: 50.3, load: 761.1 },
  { month: '2025-08', readiness: 62.7, load: 276.8 },
  { month: '2025-09', readiness: 59.9, load: 500.6 },
  { month: '2025-10', readiness: 58.9, load: 651.4 },
  { month: '2025-11', readiness: 59.4, load: 671.2 },
  { month: '2025-12', readiness: 58.8, load: 504.0 },
  { month: '2026-01', readiness: 47.9, load: 669.3 },
  { month: '2026-02', readiness: 56.1, load: 698.1 },
  { month: '2026-03', readiness: 50.8, load: 916.5 },
  { month: '2026-04', readiness: 56.5, load: 929.5 },
  { month: '2026-05', readiness: 53.8, load: 1032.7 },
];

const monthlyFitness = [
  { month: '2024-03', rhr: 45.0, vo2: 76.2 },
  { month: '2024-04', rhr: 45.1, vo2: 77.7 },
  { month: '2024-05', rhr: 45.9, vo2: 77.5 },
  { month: '2024-07', rhr: 44.9, vo2: 78.5 },
  { month: '2024-08', rhr: 44.5, vo2: 77.0 },
  { month: '2024-09', rhr: 45.8, vo2: 75.3 },
  { month: '2024-10', rhr: 43.9, vo2: 76.0 },
  { month: '2024-12', rhr: 44.9, vo2: 74.0 },
  { month: '2025-01', rhr: 44.0, vo2: 72.0 },
  { month: '2025-02', rhr: 45.2, vo2: 72.0 },
  { month: '2025-03', rhr: 45.8, vo2: 70.5 },
  { month: '2025-04', rhr: 44.1, vo2: 71.2 },
  { month: '2025-05', rhr: 44.6, vo2: 71.6 },
  { month: '2025-06', rhr: 46.5, vo2: 67.8 },
  { month: '2025-07', rhr: 46.7, vo2: 66.5 },
  { month: '2025-08', rhr: 46.4, vo2: 68.1 },
  { month: '2025-09', rhr: 45.7, vo2: 70.5 },
  { month: '2025-10', rhr: 41.4, vo2: 73.3 },
  { month: '2025-11', rhr: 42.9, vo2: 76.7 },
  { month: '2025-12', rhr: 45.5, vo2: 75.7 },
  { month: '2026-01', rhr: 44.8, vo2: 75.8 },
  { month: '2026-02', rhr: 45.0, vo2: 75.1 },
  { month: '2026-03', rhr: 44.4, vo2: 74.8 },
  { month: '2026-04', rhr: 43.8, vo2: 75.0 },
  { month: '2026-05', rhr: 41.9, vo2: 75.5 },
];

const keyRows = [
  ['activity_count', '2169', '1.49', '1.00', '8.00'],
  ['activity_duration_seconds', '2169', '3710.82', '3219.35', '70940.21'],
  ['activity_distance_m', '2169', '18742.92', '12886.79', '323787.06'],
  ['activity_avg_hr', '2163', '142.99', '143.33', '179.00'],
  ['sleep_total_seconds', '1914', '4827.84', '0.00', '53760.00'],
  ['readiness_score', '795', '60.05', '62.75', '94.00'],
  ['load_dailyTrainingLoadAcute', '901', '675.04', '681.50', '1418.50'],
  ['fitness_vo2MaxValue', '1844', '71.05', '71.00', '79.00'],
  ['wellness_restingHeartRate', '2796', '46.84', '47.00', '56.00'],
  ['wellness_totalSteps', '2811', '15015.79', '15174.00', '46917.00'],
  ['endurance_overallScore', '901', '10276.72', '10464.00', '11667.00'],
  ['hill_overallScore', '846', '58.61', '61.00', '83.00'],
];

export default function IngestionValidation() {
  return (
    <Stack gap={20}>
      <Stack gap={8}>
        <H1>Garmin Ingestion Validation</H1>
        <Text>
          Current stable snapshot: data/processed/daily_features_json_only.csv.
          A corrected FIT-inclusive rebuild is running separately because the first FIT output exposed an
          activity-column type issue.
        </Text>
        <Text tone="secondary" size="small">
          Source: Garmin export under data/raw · time range {overview.start} to {overview.end}.
        </Text>
      </Stack>

      <Grid columns={4} gap={12}>
        <Stat value={overview.rows.toLocaleString()} label="Daily rows" />
        <Stat value={overview.columns.toLocaleString()} label="Feature columns" />
        <Stat value={overview.activityDays.toLocaleString()} label="Days with activity" tone="info" />
        <Stat value={overview.totalActivities.toLocaleString()} label="Activities parsed" tone="success" />
      </Grid>

      <Callout tone="warning" title="Validation note">
        The JSON-only snapshot is coherent and usable for MVP modeling. The FIT-inclusive rebuild should increase
        activity coverage, but the corrected file should be checked before replacing this snapshot.
      </Callout>

      <Divider />

      <Grid columns={2} gap={18}>
        <Stack gap={8}>
          <H2>Feature Coverage By Source Family</H2>
          <BarChart
            horizontal
            height={360}
            categories={groupCoverage.map((row) => row.group)}
            series={[{ name: 'Days with at least one non-null feature', data: groupCoverage.map((row) => row.coveragePct), tone: 'info' }]}
            valueSuffix="%"
          />
          <Text tone="secondary" size="small">
            X-axis: coverage (% of 2,820 days). Y-axis: parsed Garmin feature family.
          </Text>
        </Stack>

        <Stack gap={8}>
          <H2>Activity Count By Year</H2>
          <BarChart
            height={320}
            categories={annual.map((row) => row.year)}
            series={[{ name: 'Activities per year', data: annual.map((row) => row.activity_count), tone: 'success' }]}
          />
          <Text tone="secondary" size="small">
            X-axis: calendar year. Y-axis: count of summarized Garmin activities.
          </Text>
        </Stack>
      </Grid>

      <Stack gap={8}>
        <H2>Recent Monthly Activity Counts</H2>
        <LineChart
          height={280}
          categories={recentMonthly.map((row) => row.month)}
          series={[{ name: 'Activities per month', data: recentMonthly.map((row) => row.activity_count), tone: 'success' }]}
          fill
        />
        <Text tone="secondary" size="small">
          X-axis: month. Y-axis: activity count. Source: summarizedActivities JSON, last 24 months in snapshot.
        </Text>
      </Stack>

      <Grid columns={2} gap={18}>
        <Stack gap={8}>
          <H3>Readiness Score And Acute Load</H3>
          <LineChart
            height={260}
            categories={monthlyMetrics.map((row) => row.month)}
            series={[
              { name: 'Readiness score (0-100)', data: monthlyMetrics.map((row) => row.readiness), tone: 'info' },
              { name: 'Acute training load / 10', data: monthlyMetrics.map((row) => Math.round(row.load / 10)), tone: 'warning' },
            ]}
          />
          <Text tone="secondary" size="small">
            X-axis: month. Y-axis: readiness points and acute load scaled by 10 for visual comparison.
          </Text>
        </Stack>

        <Stack gap={8}>
          <H3>Resting Heart Rate And VO2 Max</H3>
          <LineChart
            height={260}
            categories={monthlyFitness.map((row) => row.month)}
            series={[
              { name: 'Resting heart rate (bpm)', data: monthlyFitness.map((row) => row.rhr), tone: 'neutral' },
              { name: 'VO2 max', data: monthlyFitness.map((row) => row.vo2), tone: 'info' },
            ]}
          />
          <Text tone="secondary" size="small">
            X-axis: month. Y-axis: bpm and VO2 max. Months with missing VO2 are omitted from this plot.
          </Text>
        </Stack>
      </Grid>

      <Divider />

      <Stack gap={8}>
        <H2>Key Feature Sanity Checks</H2>
        <Table
          headers={['Metric', 'Non-null days', 'Mean', 'Median', 'Max']}
          rows={keyRows}
        />
        <Text tone="secondary" size="small">
          These are unnormalized daily aggregates. Some activity totals look large because multi-activity days are
          summed and Garmin activity exports include very long events.
        </Text>
      </Stack>
    </Stack>
  );
}
