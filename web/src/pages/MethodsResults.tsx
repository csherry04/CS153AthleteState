import { BarChart, Callout, Card, CardBody, CardHeader, Grid, H1, H2, Stack, Stat, Table, Text } from 'cursor/canvas';

const modelRows = [
  ['Naive persistence', 'Readiness(t) = Readiness(t-1)', 'Baseline sanity check', 'Reproduced by run_baselines.py'],
  ['Ridge regression', 'Tabular daily features', 'Linear baseline', 'Reproduced by run_baselines.py'],
  ['MLP', 'Tabular daily features', 'Nonlinear baseline', 'Reproduced by run_baselines.py'],
  ['Supervised TCN', '28-day multivariate windows', 'MAE 14.01 · RMSE 17.12', 'Reproduced by train_tcn.py'],
  ['Masked-pretrained TCN', 'Self-supervised reconstruction + readiness fine-tune', 'MAE 12.26 · RMSE 15.31', 'Reproduced by pretrain_masked_tcn.py + finetune_tcn_from_pretrained.py'],
];

const pipelineRows = [
  ['1', 'Garmin ingestion', 'Parse FIT/CSV/JSON/TCX/XML exports; dedupe repeated activities; aggregate to daily features.'],
  ['2', 'Feature validation', 'Check missingness, ranges, data coverage, and daily feature quality.'],
  ['3', 'Time-series windows', 'Build chronological 28-day windows without fitting transforms on future data.'],
  ['4', 'Modeling', 'Train baselines, supervised TCN, and masked-pretrained TCN for next-day readiness.'],
  ['5', 'Frontier state', 'Export embeddings, anomaly scores, nearest neighbors, and readiness forecast errors.'],
  ['6', 'Risk interpretation', 'Blend rule-based load, personalized load, learned frontier strain, and recovery context.'],
  ['7', 'Product layer', 'Local web UI and live coach API for date exploration, briefing, Q&A, and profile summaries.'],
];

export default function MethodsResults() {
  return (
    <Stack gap={20}>
      <Stack gap={8}>
        <H1>Methods & Results</H1>
        <Text>
          A concise technical summary for the CS 153 submission: what was built, how the model works, and what evidence
          supports the frontier layer.
        </Text>
      </Stack>

      <Grid columns={4} gap={12}>
        <Stat value="2,820" label="Daily Garmin rows" tone="info" />
        <Stat value="~305" label="Daily feature columns" tone="info" />
        <Stat value="2,792" label="Frontier-covered days" tone="info" />
        <Stat value="28d" label="Model lookback window" tone="warning" />
      </Grid>

      <Callout tone="info" title="Core idea">
        The project turns one athlete’s wearable export into a monitoring system: interpretable running-load rules,
        personal-history percentiles, learned TCN state embeddings, and recovery context are shown side by side instead
        of collapsed into an unexplained black-box alert.
      </Callout>

      <Card>
        <CardHeader>End-to-end pipeline</CardHeader>
        <CardBody>
          <Table headers={['Step', 'Layer', 'What happens']} rows={pipelineRows} striped />
        </CardBody>
      </Card>

      <H2>Modeling results</H2>
      <Table headers={['Model', 'Input', 'Result / role', 'Script']} rows={modelRows} striped />
      <BarChart
        categories={['Supervised TCN', 'Masked-pretrained TCN']}
        series={[
          { name: 'MAE', data: [14.01, 12.26], tone: 'warning' },
          { name: 'RMSE', data: [17.12, 15.31], tone: 'info' },
        ]}
        height={260}
      />

      <Grid columns={2} gap={12}>
        <Callout tone="success" title="What improved">
          Masked reconstruction pretraining improved next-day readiness forecasting versus the supervised-only TCN on the
          same sport-expanded daily feature set.
        </Callout>
        <Callout tone="warning" title="What this does not prove">
          This is a single-athlete retrospective system. The scores are monitoring signals, not medical diagnosis or a
          population-validated injury prediction model.
        </Callout>
      </Grid>

      <H2>What the frontier layer adds</H2>
      <Table
        headers={['Component', 'Why it exists', 'Interpretation']}
        rows={[
          ['Embedding novelty', 'Detects days whose learned 28-day state is unusual.', 'Useful for “this day looks different from normal training state.”'],
          ['Readiness forecast error', 'Measures when the model fails to predict readiness well.', 'Useful for days where the athlete-state model sees instability or mismatch.'],
          ['Reference-block similarity', 'Compares the latent state to known concerning/risky reference blocks.', 'Useful for asking whether today resembles prior periods worth monitoring.'],
          ['Frontier-integrated risk', 'Blends rules + personal load with frontier strain.', 'Useful as the headline score while preserving interpretable breakdowns.'],
        ]}
        striped
      />
    </Stack>
  );
}
