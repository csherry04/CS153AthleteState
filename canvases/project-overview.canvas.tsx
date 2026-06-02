import {
  BarChart,
  Callout,
  Card,
  CardBody,
  CardHeader,
  Code,
  CollapsibleSection,
  Divider,
  Grid,
  H1,
  H2,
  H3,
  PieChart,
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
  useCanvasState,
} from 'cursor/canvas';

const sections = [
  ['overview', 'Overview'],
  ['profile', 'Athlete profile'],
  ['alerts', 'Active alerts'],
  ['running', 'Running load'],
  ['monitoring', 'Three-track compare'],
  ['recovery', 'Recovery risk'],
  ['method', 'How it works'],
] as const;

type SectionId = (typeof sections)[number][0];

const bonePeriodRows = [
  ['2023-06-12', '2023-07-27', '46', 'high', '84', '131', 'running volume progression'],
  ['2023-08-05', '2023-08-29', '25', 'high', '82', '138', 'sustained high running volume'],
  ['2022-07-12', '2022-08-23', '43', 'high', '81', '107', 'running volume progression'],
  ['2024-03-03', '2024-03-27', '25', 'high', '79', '144', 'sustained high running volume'],
  ['2024-04-19', '2024-04-27', '9', 'high', '78', '139', 'sustained high running volume'],
  ['2024-01-16', '2024-01-25', '10', 'high', '76', '152', 'sustained high running volume'],
  ['2022-12-30', '2023-01-10', '12', 'high', '76', '114', 'sustained high running volume'],
  ['2024-02-02', '2024-02-07', '6', 'high', '76', '131', 'sustained high running volume'],
];

const boneDayRows = [
  ['2024-04-21', '95', '81', '88', '61', 'sustained high running volume', 'literature_personalized_agree_frontier_differs'],
  ['2024-01-07', '95', '70', '81', '77', 'sustained high running volume', 'all_agree'],
  ['2023-07-16', '95', '77', '84', '34', 'sustained high running volume', 'literature_personalized_agree_frontier_differs'],
  ['2023-08-15', '94', '81', '86', '60', 'sustained high running volume', 'literature_personalized_agree_frontier_differs'],
  ['2020-03-29', '94', '77', '89', '76', 'sustained high running volume', 'all_agree'],
  ['2023-08-20', '94', '77', '83', '56', 'sustained high running volume', 'literature_personalized_agree_frontier_differs'],
];

const febMar2025Rows = [
  ['2025-03-06', '60', '74', '62', 'literature_frontier_agree', 'sustained high running volume'],
  ['2025-03-05', '60', '75', '51', 'literature_frontier_agree', 'hard running session'],
  ['2025-03-02', '63', '78', '44', 'mixed_signals', 'running volume progression'],
  ['2025-03-07', '39', '58', '60', 'personalized_frontier_agree', 'running volume progression'],
];

const spring2024Rows = [
  ['2024-04-21', '81', '88', '61', 'literature_personalized_agree_frontier_differs', 'sustained high running volume'],
  ['2024-03-10', '81', '85', '57', 'literature_personalized_agree_frontier_differs', 'sustained high running volume'],
  ['2024-03-24', '77', '75', '70', 'all_agree', 'sustained high running volume'],
  ['2024-03-26', '77', '78', '66', 'literature_personalized_agree_frontier_differs', 'sustained high running volume'],
];

const frontierDisagreeRows = [
  ['2026-03-16', '60', '64', '73', 'literature_personalized_agree_frontier_differs', 'running load spike'],
  ['2026-03-15', '60', '63', '77', 'literature_personalized_agree_frontier_differs', 'hard running session'],
  ['2026-03-12', '60', '58', '73', 'literature_personalized_agree_frontier_differs', 'hard running session'],
  ['2026-01-19', '60', '77', '73', 'personalized_frontier_agree', 'sustained high running volume'],
  ['2026-01-18', '60', '76', '75', 'personalized_frontier_agree', 'hard running session'],
];

const recoveryPeriodRows = [
  ['2025-04-14', '2025-05-22', 'high', '71', 'accumulated insufficient rest'],
  ['2025-02-27', '2025-03-29', 'high', '71', 'accumulated insufficient rest'],
  ['2026-03-13', '2026-04-16', 'high', '70', 'accumulated insufficient rest'],
  ['2025-08-28', '2025-09-17', 'high', '69', 'accumulated insufficient rest'],
  ['2025-06-14', '2025-07-25', 'high', '69', 'low risk'],
];

const recoveryDayRows = [
  ['2026-03-15', '81', 'high', 'post-load recovery response'],
  ['2025-03-22', '80', 'high', 'accumulated insufficient rest'],
  ['2025-08-10', '79', 'high', 'tissue-load recovery mismatch'],
  ['2026-03-23', '78', 'high', 'tissue-load recovery mismatch'],
  ['2025-07-07', '75', 'high', 'running while under-recovered'],
];

const scoreGuideRows = [
  ['0–44', 'Low', 'Normal running-load context'],
  ['45–69', 'Moderate', 'Worth watching — load building faster than usual'],
  ['70–100', 'High', 'Reduce running volume or intensity; check recovery'],
];

const trackRows = [
  ['Literature', 'Gabbett ACWR zones, Edwards speed bands, Foster monotony/strain', '2,820 days', 'Defensible objective thresholds — no percentiles'],
  ['Personalized', 'Percentile scoring vs your running history', '2,820 days', 'Individualized progression and spikes'],
  ['Frontier', 'Accumulated TCN state: embedding novelty + negative readiness surprise + reference similarity with recovery/load-sensitive carryover', '2,792 days (28d warm-up)', 'Cumulative learned-state strain'],
  ['Recovery risk', 'Readiness, HRV, sleep + all sports', '795 days', 'Autonomic recovery lagging workload'],
];

const agreementRows = [
  ['all_agree', '1,027', 'All three tracks same level'],
  ['literature_personalized_agree_frontier_differs', '981', 'Lit + pers agree, frontier differs'],
  ['literature_frontier_agree', '369', 'Objective load + learned state align'],
  ['personalized_frontier_agree', '280', 'Individual spike + learned state align'],
  ['mixed_signals', '153', 'Literature and personalized disagree'],
  ['literature_personalized_agree', '10', 'Lit + pers agree, no frontier coverage'],
];

function SectionNav() {
  const [active, setActive] = useCanvasState<SectionId>('activeSection', 'overview');
  return (
    <Row gap={8} wrap>
      {sections.map(([id, label]) => (
        <Pill key={id} active={active === id} onClick={() => setActive(id)}>
          {label}
        </Pill>
      ))}
    </Row>
  );
}

function ActiveSection({ section }: { section: SectionId }) {
  if (section === 'profile') {
    return (
      <Stack gap={16}>
        <Callout tone="info" title="Interpretability layer">
          These canvases translate scores into strengths, risk patterns, daily actions, and frontier validation — open
          each beside the chat after regenerating outputs.
        </Callout>
        <Table
          headers={['Canvas', 'Purpose', 'Regenerate']}
          rows={[
            ['athlete-profile.canvas.tsx', 'Strengths, weaknesses, risky periods, recommendations', 'generate_athlete_profile.py'],
            ['date-explorer.canvas.tsx', 'Search any day, compare dates, full stats + insights', 'generate_date_explorer_canvas.py'],
            ['daily-briefing.canvas.tsx', 'Today’s alert tier, three tracks, 7-day trend, counterfactual', 'generate_daily_briefing.py'],
            ['bone-stress-periods.canvas.tsx', 'Detected load blocks, agreement per period, active block', 'generate_bone_stress_periods_canvas.py'],
            ['coaching-qa.canvas.tsx', 'Grounded Q&A for flagged days', 'generate_coaching_qa.py'],
            ['frontier-outcomes.canvas.tsx', 'Did frontier/rules flag before spring 2024?', 'evaluate_frontier_outcomes.py'],
          ]}
          striped
        />
        <H2>Operational alert tiers</H2>
        <Table
          headers={['Tier', 'Meaning']}
          rows={[
            ['Clear', 'No elevated running-load action'],
            ['Watch', 'One track elevated — monitor progression'],
            ['Investigate state', 'Frontier high while literature load modest — check recovery markers'],
            ['Adjust training', 'Multiple tracks agree or mixed high signals — reduce volume/intensity'],
          ]}
          striped
        />
        <Text tone="secondary" size="small">
          Full pipeline: export_full_history_embeddings.py → score_athlete_risk.py → evaluate_frontier_outcomes.py →
          generate_daily_briefing.py → generate_bone_stress_periods_canvas.py → generate_coaching_qa.py →
          generate_athlete_profile.py
        </Text>
      </Stack>
    );
  }

  if (section === 'overview') {
    return (
      <Stack gap={16}>
        <Callout tone="info" title="What this system does">
          Scores every day from Garmin data using two philosophies side by side: literature-backed objective thresholds
          (Gabbett, Edwards, Foster) and personalized percentiles vs your history. Where the TCN has coverage, a third
          frontier track adds embedding novelty and negative readiness surprise. For a plain-language read of your
          strengths, risk patterns, and what to adjust, open the Athlete profile canvas.
        </Callout>
        <Grid columns={4} gap={12}>
          <Stat value="2,820" label="Days of Garmin data" tone="info" />
          <Stat value="2,792" label="Frontier-covered days" tone="info" />
          <Stat value="48" label="Running-load blocks" tone="warning" />
          <Stat value="16" label="Recovery-risk blocks" tone="warning" />
        </Grid>
        <H2>Four parallel tracks</H2>
        <Table headers={['Track', 'Inputs', 'Coverage', 'Use when']} rows={trackRows} striped />
        <H2>What each score means</H2>
        <Callout tone="info" title="Plain-English version">
          The system is not one magic number. It separates interpretable running-load rules, your personal history, the
          learned frontier model, and recovery state. The headline Frontier-integrated risk is useful because it blends
          the interpretable load signal with the model signal, but the breakdown explains why a day was flagged.
        </Callout>
        <Table
          headers={['Display name', 'What it is asking', 'What drives it', 'How to use it']}
          rows={[
            ['Literature rule score', 'Would a standard sports-science rule flag this running pattern?', 'Running workload ratio, speed/intensity bands, monotony, strain, and progression.', 'Use this as the most objective/interpretable check. If high, the load pattern is risky even before considering your personal baseline.'],
            ['Personal history score', 'Is this unusual for this athlete specifically?', 'Percentiles against your own recent and historical running volume, load, intensity, and progression.', 'Use this to catch “big for you” days. It can be high even when literature rules are only moderate.'],
            ['Rules + personal load risk', 'Do the objective rules and personal baseline together suggest bone-stress load?', 'Blend of literature rule score and personal history score, plus spike/progression logic.', 'Use this to understand the plain running-load reason. This is the best explanation of mileage/load-driven risk.'],
            ['Frontier state score', 'Does learned-state strain appear to be accumulating?', 'Embedding novelty, negative readiness surprise, and reference similarity with recovery/load-sensitive carryover.', 'Use this as the model-based frontier score. It is cumulative, so one quiet day does not erase a prior learned-state spike.'],
            ['Frontier-integrated risk', 'What is the best headline score combining load logic with the frontier model?', '65% Rules + personal load risk, 35% Frontier state score when model coverage exists.', 'Use this first on pages like Date Explorer. Then inspect the component scores to understand whether the warning came from load, the model, or both.'],
            ['Recovery risk', 'Is recovery/autonomic state poor relative to recent workload?', 'Readiness, HRV, sleep/body battery, accumulated insufficient rest, and running while under-recovered.', 'Use this separately from bone-stress load. It explains whether the body looks under-recovered even if running load is not extreme.'],
          ]}
          striped
        />
        <Grid columns={3} gap={12}>
          <Callout tone="success" title="All scores low">
            Normal context. No strong load, model, or recovery warning. Keep progression gradual.
          </Callout>
          <Callout tone="warning" title="One score high">
            Investigate the source. Literature/personal high usually means load management; frontier high means check
            hidden strain; recovery high means protect sleep/readiness.
          </Callout>
          <Callout tone="danger" title="Multiple scores high">
            Stronger signal. If load + frontier + recovery align, reduce intensity/volume and avoid stacking hard days.
          </Callout>
        </Grid>
        <H2>How to read a score</H2>
        <Table
          headers={['Range', 'Level', 'Practical meaning']}
          rows={[
            ['0–44', 'Low', 'Normal or controlled context for that signal. Not zero risk, but no major alert from this track.'],
            ['45–69', 'Moderate', 'Worth watching. The track sees load building, model strain, or recovery pressure, but not an extreme alert.'],
            ['70–100', 'High', 'Actionable warning. Reduce or modify training if this aligns with symptoms, poor recovery, or multiple high tracks.'],
          ]}
          striped
        />
        <H2>How to interpret disagreements</H2>
        <Table
          headers={['Pattern', 'Likely meaning', 'What to check']}
          rows={[
            ['Rules + personal high, frontier low', 'Running load is objectively/personally high, but the learned state does not look unusual.', 'Still manage load; the model is not a free pass. Check recent mileage and hard-session stacking.'],
            ['Frontier high, rules + personal low', 'Accumulated learned-state strain is high without a classic mileage spike.', 'Check readiness, HRV, sleep, cross-training fatigue, illness/stress, and whether the day resembles prior risky periods.'],
            ['Personal high, literature low', 'This is big relative to your own history but not objectively extreme.', 'Progression may be too sharp for you personally. Consider easing volume or intensity.'],
            ['Literature high, personal low', 'The day violates general load rules, but this athlete has handled similar loads before.', 'Still respect the objective warning, especially if recovery is poor or symptoms exist.'],
            ['All agree high', 'The strongest signal: objective load, personal history, and/or learned state are aligned.', 'Treat as a real training-management warning. Reduce intensity/volume and prioritize recovery.'],
          ]}
          striped
        />
        <Text tone="secondary" size="small">
          Scores are decision-support signals, not medical diagnosis. The numbers explain training and recovery context;
          symptoms, pain, and clinical judgment still override the model.
        </Text>
      </Stack>
    );
  }

  if (section === 'alerts') {
    return (
      <Stack gap={16}>
        <Callout tone="warning" title="Prospective monitoring">
          Blocks are clusters of high running-load days (typically 1–7 weeks), not months-long stretches of
          background accumulated state. The algorithm scans all history without knowing injury dates.
        </Callout>
        <H2>Running-load blocks (bone-stress track)</H2>
        <Text tone="secondary" size="small">
          Source: top_bone_stress_periods.csv · ranked by peak accumulated state
        </Text>
        <Table
          headers={['Start', 'End', 'Days', 'Level', 'Peak state', 'Peak 7d km', 'Pattern']}
          rows={bonePeriodRows}
          rowTone={bonePeriodRows.map((row) => (row[3] === 'high' ? 'danger' : 'warning'))}
          striped
        />
        <H2>Recovery-risk blocks</H2>
        <Text tone="secondary" size="small">
          Source: top_risk_periods.csv · general preparedness, all sports
        </Text>
        <Table
          headers={['Start', 'End', 'Level', 'Peak state', 'Dominant pattern']}
          rows={recoveryPeriodRows}
          rowTone={recoveryPeriodRows.map((row) => (row[2] === 'high' ? 'danger' : 'warning'))}
          striped
        />
        <CollapsibleSection title="Regenerate alerts from latest data" count={5}>
          <Stack gap={6}>
            <Text size="small"><Code>.venv/bin/python scripts/export_full_history_embeddings.py</Code></Text>
            <Text size="small"><Code>.venv/bin/python scripts/score_athlete_risk.py</Code></Text>
            <Text size="small"><Code>.venv/bin/python scripts/compare_monitoring_signals.py</Code></Text>
            <Text size="small"><Code>.venv/bin/python scripts/generate_athlete_feedback.py</Code></Text>
            <Text size="small"><Code>.venv/bin/python scripts/evaluate_bone_stress_outcomes.py</Code></Text>
          </Stack>
        </CollapsibleSection>
      </Stack>
    );
  }

  if (section === 'running') {
    return (
      <Stack gap={16}>
        <Callout tone="info" title="Running-only load monitor">
          Three internal tracks feed one operational alert. Literature uses fixed anchors (ACWR sweet spot 0.8–1.3,
          danger ≥1.5; Edwards speed bands; Foster monotony &gt;2.0). Personalized uses percentiles. Accumulated state
          decays slowly (0.91/day) so tissue load can stay elevated after volume drops.
        </Callout>
        <Grid columns={4} gap={12}>
          <Stat value="784" label="Combined high days" tone="danger" />
          <Stat value="438" label="Literature high days" tone="warning" />
          <Stat value="580" label="Personalized high days" tone="warning" />
          <Stat value="84" label="Peak accumulated state" tone="info" />
        </Grid>
        <H2>Top running-load days</H2>
        <Text tone="secondary" size="small">
          Source: top_bone_stress_days.csv · severity rank · Lit/Pers/Fr = literature, personalized, frontier scores
        </Text>
        <Table
          headers={['Date', 'Severity', 'Lit', 'Pers', 'Fr', 'Reason', 'Agreement']}
          rows={boneDayRows}
          columnAlign={['left', 'right', 'right', 'right', 'right', 'left', 'left']}
          rowTone={boneDayRows.map(() => 'danger')}
          striped
        />
        <H2>Literature anchors (literature track)</H2>
        <Table
          headers={['Signal', 'Threshold', 'Source']}
          rows={[
            ['ACWR sweet spot', '0.8 – 1.3', 'Gabbett [1,2,45]'],
            ['ACWR danger zone', '≥ 1.5', 'Gabbett [1,2,45]'],
            ['Edwards speed bands', '2.5 / 3.5 / 4.5 m/s', 'Edwards [9]'],
            ['Foster monotony', '> 2.0 elevated', 'Foster [5]'],
            ['Volume progression', 'Chronic vs acute load ratio', 'Napier / Gabbett [8]'],
          ]}
          striped
        />
        <H2>Personalized components (percentile blend)</H2>
        <Table
          headers={['Signal', 'Weight', 'Why']}
          rows={[
            ['7-day composite running load', '25%', 'Recent volume + intensity exposure'],
            ['28-day composite running load', '18%', 'Chronic running load baseline'],
            ['Volume progression / ACWR', '15%', 'Rapid ramp vs chronic load'],
            ['Speed / HR intensity', '12%', 'Magnitude matters, not just distance'],
            ['Workout difficulty (Edwards-primary)', '12%', 'Hard sessions when speed band is genuinely high'],
            ['ACWR + Foster strain', '18%', 'Workload ratio and repeated patterns'],
          ]}
          striped
        />
        <Text tone="secondary" size="small">
          Full narratives: outputs/analysis/athlete_bone_stress_feedback.md
        </Text>
      </Stack>
    );
  }

  if (section === 'monitoring') {
    return (
      <Stack gap={16}>
        <Callout tone="info" title="Why compare tracks?">
          Disagreement is the research signal. Literature high but personalized not = objective concern your history
          would miss. Personalized high but literature not = percentile spike that is objectively modest. Frontier high
          but literature not = multivariate strain the rule engine cannot express.
        </Callout>
        <Grid columns={3} gap={12}>
          <Stat value="163" label="Lit high, personalized not" tone="warning" />
          <Stat value="305" label="Personalized high, lit not" tone="warning" />
          <Stat value="172" label="Frontier high, lit not" tone="danger" />
        </Grid>
        <Text tone="secondary" size="small">
          Frontier covers 2,792 / 2,820 days (first 28 days need a lookback window). Negative readiness surprise only exists
          on days where Garmin readiness predictions and actuals are both available. Negative embedding anomaly = low novelty (0), not negative strain.
          Tag `literature_personalized_agree_frontier_differs` means load tracks agree but frontier does not.
        </Text>
        <Callout tone="warning" title="What frontier means now">
          The displayed frontier score is the accumulated frontier state, not raw daily model surprise. It rises with
          unusual learned-state strain and decays gradually based on recovery/load context.
        </Callout>
        <H2>Agreement tags (full history)</H2>
        <Text tone="secondary" size="small">Source: monitoring_signal_summary.json</Text>
        <Table headers={['Tag', 'Days', 'Meaning']} rows={agreementRows} striped />
        <H3>Spring 2024 (labeled BSI window — validation only)</H3>
        <Text tone="secondary" size="small">
          Mar 24: all tracks high; accumulated frontier state stays elevated across the March load block.
        </Text>
        <Table
          headers={['Date', 'Lit', 'Pers', 'Fr', 'Agreement', 'Reason']}
          rows={spring2024Rows}
          columnAlign={['left', 'right', 'right', 'right', 'left', 'left']}
          striped
        />
        <H3>Frontier high, literature not (recent examples)</H3>
        <Text tone="secondary" size="small">
          Source: latest athlete_bone_stress_scores.csv · negative readiness surprise / embedding novelty without objective load spike
        </Text>
        <Table
          headers={['Date', 'Lit', 'Pers', 'Fr', 'Agreement', 'Reason']}
          rows={frontierDisagreeRows}
          columnAlign={['left', 'right', 'right', 'right', 'left', 'left']}
          rowTone={frontierDisagreeRows.map(() => 'danger')}
          striped
        />
        <CollapsibleSection title="Regenerate comparison report" count={1}>
          <Text size="small"><Code>.venv/bin/python scripts/compare_monitoring_signals.py</Code></Text>
        </CollapsibleSection>
      </Stack>
    );
  }

  if (section === 'recovery') {
    return (
      <Stack gap={16}>
        <Callout tone="success" title="Recovery risk ≠ anomaly">
          A rest day can look unusual in the embedding without being risky. This track only flags days when recovery
          markers (readiness, HRV, sleep) look poor relative to recent workload — including cycling and hiking fatigue.
          Embedding novelty nudges recovery risk +15% when strain ≥40; it does not drive bone-stress scores alone.
        </Callout>
        <Grid columns={3} gap={12}>
          <Stat value="795" label="Days scored" tone="info" />
          <Stat value="71" label="Peak accumulated state" tone="danger" />
          <Stat value="16" label="Risk blocks detected" tone="warning" />
        </Grid>
        <H2>Top recovery-risk days</H2>
        <Text tone="secondary" size="small">Source: top_risk_days.csv</Text>
        <Table
          headers={['Date', 'Score', 'Level', 'Reason']}
          rows={recoveryDayRows}
          columnAlign={['left', 'right', 'left', 'left']}
          rowTone={recoveryDayRows.map(() => 'danger')}
          striped
        />
        <H2>Score components (simplified)</H2>
        <Table
          headers={['Component', 'Question it asks']}
          rows={[
            ['Recovery strain', 'Are readiness, HRV, RHR, or sleep off your baseline?'],
            ['Prior workload', 'Was yesterday or the past week unusually hard?'],
            ['Metabolic fatigue', 'High cycling/running duration weighted for fatigue?'],
            ['Tissue load', 'High running/hiking impact while under-recovered?'],
            ['Insufficient rest', 'Has load stayed high for 7+ days without recovery?'],
            ['Accumulated state', 'Does strain carry forward day to day (decay 0.86)?'],
          ]}
          striped
        />
        <Text tone="secondary" size="small">
          Full narratives: outputs/analysis/athlete_risk_feedback.md · SCIENTIFIC_RATIONALE.md
        </Text>
      </Stack>
    );
  }

  return (
    <Stack gap={16}>
      <H2>Pipeline</H2>
      <Table
        headers={['Step', 'Script', 'Output']}
        rows={[
          ['1', 'src/garmin_pipeline.py', 'Daily features from Garmin export'],
          ['2', 'scripts/export_full_history_embeddings.py', 'Full-history TCN embeddings + predictions'],
          ['3', 'scripts/pretrain_masked_tcn.py + finetune', 'Train readiness model (only when retraining)'],
          ['4', 'scripts/score_athlete_risk.py', 'Literature + personalized + frontier + alert tiers'],
          ['5', 'scripts/evaluate_frontier_outcomes.py', 'Frontier vs rules lead-time validation'],
          ['6', 'scripts/compare_monitoring_signals.py', 'Track agreement / disagreement report'],
          ['7', 'scripts/generate_daily_briefing.py', 'Daily operational canvas'],
          ['8', 'scripts/generate_athlete_profile.py', 'Athlete profile canvas + markdown'],
          ['9', 'scripts/pretrain_contrastive_encoder.py', 'Prototype contrastive encoder fine-tune'],
          ['10', 'scripts/generate_athlete_feedback.py', 'Readable day/period explanations'],
        ]}
        striped
      />
      <H2>Key output files</H2>
      <Table
        headers={['File', 'Contents']}
        rows={[
          ['athlete_profile.md', 'Interpretable strengths, risks, and recommendations'],
          ['athlete_profile.json', 'Structured profile data for the athlete profile canvas'],
          ['athlete_bone_stress_scores.csv', 'Full history with literature, personalized, frontier columns (2,820 rows)'],
          ['monitoring_signal_comparison.csv', 'Per-day deltas across tracks'],
          ['monitoring_signal_disagreements.csv', 'Days where literature ≠ personalized'],
          ['monitoring_signal_comparison.md', 'Human-readable comparison summary'],
          ['athlete_bone_stress_periods.csv', 'Detected running-load blocks'],
          ['athlete_risk_scores.csv', 'Recovery risk on modeled window (795 rows)'],
          ['bone_stress_outcome_evaluation.md', 'Retrospective check — not used for scoring'],
        ]}
        striped
      />
      <Callout tone="info" title="Validation vs monitoring">
        config/outcome_events.json supplies a reference embedding centroid for spring 2024 similarity only. Scoring
        thresholds are not tuned to labeled injury dates — alerts come from the wearable data stream and model outputs.
      </Callout>
    </Stack>
  );
}

export default function ProjectOverview() {
  const [active] = useCanvasState<SectionId>('activeSection', 'overview');
  return (
    <Stack gap={20}>
      <Stack gap={8}>
        <H1>Athlete monitoring</H1>
        <Text>
          Prospective load and recovery monitoring from Garmin data. Running load now runs three parallel tracks —
          literature (defensible), personalized (individualized), and frontier (TCN-learned). Use Three-track compare
          to see where they agree or diverge.
        </Text>
        <Text tone="secondary" size="small">
          Data 2018–2026 · run export_full_history_embeddings.py then score_athlete_risk.py after new exports ·
          interpretable summary: athlete-profile.canvas.tsx
        </Text>
      </Stack>
      <SectionNav />
      <Divider />
      <ActiveSection section={active} />
    </Stack>
  );
}
