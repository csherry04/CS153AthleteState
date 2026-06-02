import { Callout, Card, CardBody, CardHeader, Grid, H1, H2, Stack, Stat, Table, Text } from 'cursor/canvas';

const agreementRows = [
  ['Literature high days', '438', 'Objective sports-science style running-load rules.'],
  ['Personalized high days', '580', 'Percentile-based alerts versus this athlete’s own history.'],
  ['Rules + personal high days', '784', 'Operational load-risk score combining literature and personal context.'],
  ['Frontier high days', '190 / 2,792', 'More selective learned-state signal.'],
  ['Frontier high, literature not', '151', 'Potential hidden-strain/model-signal days without objective high literature load.'],
  ['Personalized high, literature not', '305', 'Days that are big for this athlete even if not objectively extreme.'],
];

const validationRows = [
  ['Spring 2024 bone-stress reference', 'Frontier high first appeared 52 days before evaluation end; all-track agreement appeared 51 days before.', 'Retrospective validation only; scoring did not use event labels.'],
  ['Feb–Mar 2025 bike-heavy running ramp', 'Frontier high and integrated high appeared 56 days before the reference end.', 'Reference period, not a diagnosed injury label.'],
  ['Model forecast benchmark', 'Masked-pretrained TCN improved MAE from 14.01 to 12.26 versus supervised-only TCN.', 'Shows representation learning helped readiness forecasting.'],
  ['Agreement analysis', '667 all-agree days; 1,341 days where load tracks agree but frontier differs.', 'Disagreement is analyzed rather than treated as a bug.'],
];

const reproduceRows = [
  ['Install Python deps', 'pip install -r requirements.txt'],
  ['Run backend', 'python run_coach_api.py'],
  ['Run frontend', 'cd web && npm run dev'],
  ['Validate data', 'python scripts/validate_daily_features.py'],
  ['Build windows', 'python scripts/build_timeseries_dataset.py'],
  ['Run baselines', 'python scripts/run_baselines.py'],
  ['Train supervised TCN', 'python scripts/train_tcn.py'],
  ['Pretrain + fine-tune', 'python scripts/pretrain_masked_tcn.py && python scripts/finetune_tcn_from_pretrained.py'],
  ['Score risk', 'python scripts/score_athlete_risk.py'],
  ['Regenerate pages', 'python scripts/generate_date_explorer_canvas.py && python scripts/generate_daily_briefing.py'],
];

export default function EvaluationReproducibility() {
  return (
    <Stack gap={20}>
      <Stack gap={8}>
        <H1>Evaluation & Reproducibility</H1>
        <Text>
          Evidence, limitations, and practical commands for reproducing the local demo and the main analysis pipeline.
        </Text>
      </Stack>

      <Grid columns={4} gap={12}>
        <Stat value="12.26" label="Best readiness MAE" tone="success" />
        <Stat value="15.31" label="Best readiness RMSE" tone="success" />
        <Stat value="667" label="All-agree days" tone="info" />
        <Stat value="151" label="Frontier high, lit not" tone="warning" />
      </Grid>

      <Card>
        <CardHeader>Evaluation evidence</CardHeader>
        <CardBody>
          <Table headers={['Evidence type', 'Result', 'Caveat']} rows={validationRows} striped />
        </CardBody>
      </Card>

      <H2>Score distribution and agreement checks</H2>
      <Table headers={['Metric', 'Count', 'Why it matters']} rows={agreementRows} striped />

      <Grid columns={2} gap={12}>
        <Callout tone="success" title="Why this is enough evidence for a class project">
          The project includes baselines, model comparison, retrospective event checks, agreement analysis, and explicit
          limitations. That directly supports the claims made in the demo.
        </Callout>
        <Callout tone="warning" title="Main limitations">
          Single-athlete data, private Garmin exports, incomplete readiness coverage, heuristic thresholds, and
          retrospective references. The system is a monitoring and explanation tool, not a clinical predictor.
        </Callout>
      </Grid>

      <H2>Reproducibility checklist</H2>
      <Table headers={['Task', 'Command']} rows={reproduceRows} striped />
      <Callout tone="info" title="Private data note">
        Raw Garmin exports and large generated artifacts are intentionally ignored. The public repo should include code,
        configuration, documentation, and enough generated demo outputs to understand the system without exposing private
        health data.
      </Callout>
    </Stack>
  );
}
