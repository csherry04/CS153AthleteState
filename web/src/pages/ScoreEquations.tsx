import { Callout, Card, CardBody, CardHeader, Code, H1, H2, Stack, Table, Text } from '@/canvas';

const modelRows = [
  ['Supervised TCN', '14.01', '17.12', '28-day sequence model trained directly on readiness'],
  ['Masked-pretrained TCN', '12.26', '15.31', 'Self-supervised reconstruction pretraining, then readiness fine-tune'],
  ['Ridge regression', '18.52', '22.62', 'Linear tabular baseline'],
  ['MLP', '20.74', '25.35', 'Nonlinear tabular baseline'],
];

const equationRows = [
  [
    'Literature score',
    'max(weighted literature blend, progression spike, monotony spike, hard-session spike)',
    'Objective sports-science anchors: weekly volume, ACWR, Edwards speed bands, Foster monotony/strain.',
  ],
  [
    'Personalized score',
    '.25*7d load + .18*28d load + .15*progression + .12*intensity + .12*workout + .10*ACWR + .08*monotony',
    'Same training-load ideas, but scored against this athlete’s own historical distribution.',
  ],
  [
    'Rules + personal load risk',
    'max(.50*literature + .50*personalized, progression spike, ACWR spike, under-recovered running, monotony block, intensity block)',
    'Main interpretable running-load score. Lets one strong mechanism drive the alert.',
  ],
  [
    'Accumulated load state',
    'state[t] = .91*state[t-1] + .09*daily load contribution',
    'Slow-decay tissue/load carryover. Can stay high after mileage drops.',
  ],
  [
    'Frontier strain',
    '.40*embedding novelty + .35*negative readiness surprise + .25*reference similarity',
    'Raw learned-state signal from TCN embeddings and readiness prediction behavior.',
  ],
  [
    'Accumulated frontier state',
    'rise quickly toward frontier strain; decay by .88-.97 depending on load/recovery context',
    'Displayed frontier score. Easier to jump up than crash down.',
  ],
  [
    'Frontier-integrated risk',
    '.65*rules+personal load risk + .35*accumulated frontier state',
    'Headline risk score. Keeps interpretable load logic as the backbone.',
  ],
  [
    'Recovery strain',
    '.45*readiness risk + .20*HRV risk + .15*resting-HR risk + .10*sleep risk + .10*body-battery risk',
    'Separate recovery-context track, not the same as running bone-stress load.',
  ],
];

const componentRows = [
  ['Daily load contribution', '.22*7d load + .22*28d load + .15*progression + .16*intensity + .12*workout + .13*monotony'],
  ['Running composite load', 'distance + .45*duration*speed + elevation + 2500*aerobic TE + 5000*anaerobic TE + 30*HR-hours'],
  ['ACWR', '4 * 7-day running load / 28-day running load'],
  ['Foster monotony', 'mean daily load / standard deviation daily load'],
  ['Foster strain', 'weekly load * monotony'],
  ['Negative readiness surprise', 'max(predicted readiness - actual readiness, 0)'],
  ['Reference similarity', 'cosine similarity(today embedding, spring 2024 reference embedding)'],
];

export default function ScoreEquations() {
  return (
    <Stack gap={20}>
      <Stack gap={8}>
        <H1>Score Equations</H1>
        <Text>
          Compact formulas for explaining how the monitoring scores are computed. These are presentation-level
          equations; the source code clamps scores to 0-100 and handles missing values/edge cases.
        </Text>
      </Stack>

      <Callout tone="warning" title="How to read these">
        The scores are monitoring heuristics, not medical diagnosis. Low/moderate/high thresholds are generally 45 and
        70, while accumulated load uses 45 and 65.
      </Callout>

      <Card>
        <CardHeader>Model forecast results</CardHeader>
        <CardBody>
          <Stack gap={12}>
            <Table headers={['Model', 'Test MAE', 'Test RMSE', 'Role']} rows={modelRows} striped />
            <Text>
              The masked-pretrained TCN improves test MAE by about 12.5% versus the supervised-only TCN and performs
              substantially better than the tabular baselines. The model also provides the learned 28-day state embedding
              used by the frontier layer.
            </Text>
          </Stack>
        </CardBody>
      </Card>

      <H2>Main score formulas</H2>
      <Table headers={['Score', 'Equation', 'Interpretation']} rows={equationRows} striped />

      <H2>Supporting terms</H2>
      <Table headers={['Term', 'Formula']} rows={componentRows} striped />

      <Callout tone="info" title="Frontier flow">
        <Code>
          28-day window -&gt; TCN readiness model -&gt; embedding -&gt; novelty / readiness surprise / reference similarity
          -&gt; accumulated frontier state -&gt; integrated risk
        </Code>
      </Callout>
    </Stack>
  );
}
