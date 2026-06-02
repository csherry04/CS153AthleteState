import {
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
} from 'cursor/canvas';

const profile = {
  "snapshot": {
    "dateStart": "2018-08-26",
    "dateEnd": "2026-05-15",
    "totalDays": 2820,
    "runDays": 2053,
    "cycleDays": 211,
    "medianRunKm": 12.7,
    "boneHighDays": 784,
    "recoveryHighDays": 35,
    "bonePeriods": 48,
    "recoveryPeriods": 15
  },
  "identity": "Predominantly a high-frequency runner who uses cycling for non-impact work. Alerts are usually about how fast running volume changes, not a single hard session in isolation.",
  "strengths": [
    {
      "title": "High-volume tolerance when progression is gradual",
      "detail": "You log many 100 km+ running weeks (407 days in that band). Only 63% of those days flag high load \u2014 big blocks are not automatically risky for you when the ramp is controlled."
    },
    {
      "title": "Recovery risk usually decoupled from running load",
      "detail": "Only 10 days show both high running-load and high recovery strain. Most running stress alerts are about volume patterns, not simultaneous autonomic collapse."
    },
    {
      "title": "Strong cycling complement",
      "detail": "Running dominates (2053 active run days vs 211 ride days in the export), but cycling provides non-impact load. Typical run is ~12.7 km \u2014 you accumulate volume through frequency more than single monster days."
    }
  ],
  "weaknesses": [
    {
      "title": "Volume progression is your main flag",
      "detail": "301 high-load days were driven by progression vs 276 by sustained volume. Steep ramps relative to your recent baseline trigger alerts more than absolute km alone."
    },
    {
      "title": "Personalized alerts exceed literature thresholds",
      "detail": "305 days were high on your percentile track but not on Gabbett/Edwards/Foster rules \u2014 you are sensitive to rapid changes vs your own history even when absolute load looks modest."
    },
    {
      "title": "Multivariate strain without obvious load (frontier)",
      "detail": "172 days had high learned-state strain while literature load was low. The model sometimes sees recovery/load decoupling that rule scores miss \u2014 worth checking sleep, HRV, and mixed sport fatigue on those days."
    },
    {
      "title": "Alerts during modest weekly running",
      "detail": "276 moderate/high days occurred with <40 km/week running \u2014 often during bike-heavy blocks or after a relative ramp. Percentile progression still fires even when absolute km is low."
    }
  ],
  "recommendations": [
    {
      "priority": "high",
      "action": "Cap weekly running increases to ~10\u201315% when returning from bike-heavy blocks",
      "why": "Progression flags dominate your alert history; Feb\u2013Mar 2025 and similar blocks show percentile spikes without extreme absolute load."
    },
    {
      "priority": "high",
      "action": "After 2+ consecutive high-load running days, insert a down week or cross-train day before adding km",
      "why": "Foster monotony median on high-load days is 2.2; repeated patterns amplify strain."
    },
    {
      "priority": "medium",
      "action": "When frontier is high but literature is low, check readiness/HRV before adding intensity",
      "why": "These are days where the TCN sees atypical multivariate state \u2014 negative readiness surprise or embedding drift \u2014 not just km."
    },
    {
      "priority": "medium",
      "action": "Use Edwards speed bands: keep most volume below elevated band; limit high-magnitude sessions",
      "why": "Hard-session flags often coincide with elevated/high-magnitude speed bands (85 high-magnitude run days in history)."
    },
    {
      "priority": "low",
      "action": "Track agreement tags: investigate when all three tracks say high",
      "why": "Only 1027 all-agree days in full history \u2014 those are your strongest convergence signals."
    }
  ],
  "trackInsights": [
    {
      "track": "Literature",
      "reads_as": "Objective load guardrails",
      "your_pattern": "438 high days. Most high-load weeks sit in ACWR sweet spot/elevated, not always danger zone \u2014 literature confirms volume exposure more than calling every week extreme."
    },
    {
      "track": "Personalized",
      "reads_as": "Your percentile baseline",
      "your_pattern": "580 high days \u2014 305 more than literature. You ramp harder vs yourself than absolute thresholds suggest."
    },
    {
      "track": "Frontier",
      "reads_as": "Learned multivariate strain",
      "your_pattern": "2792 scored days; 226 high. Peaks when embedding novelty, negative readiness surprise, or reference-block similarity spike \u2014 often around labeled spring 2024 window and selected 2024\u20132025 dates."
    }
  ],
  "riskWindows": [
    {
      "start": "2023-06-12",
      "end": "2023-07-27",
      "days": "46",
      "peakKm": "131 km",
      "pattern": "running volume progression",
      "summary": "Running ramped quickly (131 km peak week) from 2023-06-12 to 2023-07-27."
    },
    {
      "start": "2023-08-05",
      "end": "2023-08-29",
      "days": "25",
      "peakKm": "138 km",
      "pattern": "sustained high running volume",
      "summary": "Sustained high weekly running (138 km peak) over 25 days."
    },
    {
      "start": "2022-07-12",
      "end": "2022-08-23",
      "days": "43",
      "peakKm": "107 km",
      "pattern": "running volume progression",
      "summary": "Running ramped quickly (107 km peak week) from 2022-07-12 to 2022-08-23."
    },
    {
      "start": "2024-03-03",
      "end": "2024-03-27",
      "days": "25",
      "peakKm": "144 km",
      "pattern": "sustained high running volume",
      "summary": "Sustained high weekly running (144 km peak) over 25 days."
    },
    {
      "start": "2024-04-19",
      "end": "2024-04-27",
      "days": "9",
      "peakKm": "139 km",
      "pattern": "sustained high running volume",
      "summary": "Sustained high weekly running (139 km peak) over 9 days."
    },
    {
      "start": "2024-01-16",
      "end": "2024-01-25",
      "days": "10",
      "peakKm": "152 km",
      "pattern": "sustained high running volume",
      "summary": "Sustained high weekly running (152 km peak) over 10 days."
    }
  ],
  "recoveryWindows": [
    {
      "start": "2025-08-26",
      "end": "2025-09-20",
      "pattern": "accumulated insufficient rest"
    },
    {
      "start": "2024-06-07",
      "end": "2024-08-03",
      "pattern": "running while under-recovered"
    },
    {
      "start": "2024-08-24",
      "end": "2024-09-28",
      "pattern": "accumulated insufficient rest"
    }
  ],
  "spring2024Note": "Labeled spring 2024 window: 41 high running-load days, mostly sustained volume (60 days). All three tracks agreed on several peak days in March \u2014 used for validation, not to tune scores.",
  "latestOperational": {
    "date": "2026-05-15",
    "tier": "watch",
    "label": "Watch",
    "recommendation": "Monitor closely \u2014 sustained high running volume. Sustained volume is the driver (~72 km/week). A recovery week at 50\u201360% of recent weekly km would reduce accumulated load.",
    "counterfactual": "Sustained volume is the driver (~72 km/week). A recovery week at 50\u201360% of recent weekly km would reduce accumulated load.",
    "archetype": "Bone stress injury (spring 2024)",
    "neighbors": "Latent state resembles 2024-01-06, 2025-11-08, 2026-05-02.",
    "accumulatedState": 70.1,
    "run7Km": 71.5
  },
  "activePeriod": {
    "start": "2026-04-22",
    "end": "2026-05-08",
    "level": "high",
    "summary": "Sustained high weekly running (109 km peak) over 17 days."
  },
  "charts": {
    "highBoneDaysByYear": {
      "categories": [
        "2018",
        "2019",
        "2020",
        "2021",
        "2022",
        "2023",
        "2024",
        "2025",
        "2026"
      ],
      "values": [
        25,
        69,
        71,
        63,
        121,
        175,
        108,
        103,
        49
      ]
    },
    "highDayReasons": {
      "labels": [
        "running volume progression",
        "sustained high running volume",
        "hard running session",
        "running load spike",
        "elevated running workload ratio"
      ],
      "values": [
        301,
        276,
        139,
        57,
        11
      ]
    }
  }
} as const;

const sections = [
  ['overview', 'Overview'],
  ['strengths', 'Strengths'],
  ['risks', 'Risk patterns'],
  ['windows', 'Risky periods'],
  ['tracks', 'How to read scores'],
  ['actions', 'What to improve'],
] as const;

type SectionId = (typeof sections)[number][0];

function SectionNav() {
  const [active, setActive] = useCanvasState<SectionId>('profileSection', 'overview');
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

function BulletCards({ items, tone }: { items: ReadonlyArray<{ title: string; detail: string }>; tone: 'success' | 'warning' | 'info' }) {
  return (
    <Stack gap={12}>
      {items.map((item) => (
        <Callout key={item.title} tone={tone} title={item.title}>
          {item.detail}
        </Callout>
      ))}
    </Stack>
  );
}

function ActiveSection({ section }: { section: SectionId }) {
  const snap = profile.snapshot;
  const charts = profile.charts;

  if (section === 'overview') {
    return (
      <Stack gap={16}>
        <Callout tone="info" title="Your training fingerprint">
          {profile.identity}
        </Callout>
        {profile.activePeriod ? (
          <Callout tone="warning" title={`Active running-load period (${profile.activePeriod.start} → ${profile.activePeriod.end})`}>
            {profile.activePeriod.summary} Peak accumulated state during detected blocks is tracked in the windows tab.
          </Callout>
        ) : null}
        <Card>
          <CardHeader>Latest operational snapshot ({profile.latestOperational.date})</CardHeader>
          <CardBody>
            <Grid columns={3} gap={12}>
              <Stat value={profile.latestOperational.label} label="Alert tier" tone="warning" />
              <Stat value={String(profile.latestOperational.run7Km)} label="7-day run km" tone="info" />
              <Stat value={String(profile.latestOperational.accumulatedState)} label="Accumulated load state" tone="warning" />
            </Grid>
            <Text tone="secondary" size="small">
              Accumulated load state is a slow-decay running strain score. It blends recent 7-day/28-day load, ramp rate,
              intensity, workouts, and monotony, then carries that strain forward so risk can linger after mileage eases.
            </Text>
            <Divider />
            <Text>{profile.latestOperational.recommendation}</Text>
            {profile.latestOperational.counterfactual ? (
              <Text tone="secondary" size="small">{profile.latestOperational.counterfactual}</Text>
            ) : null}
            {profile.latestOperational.archetype ? (
              <Text tone="secondary" size="small">Reference pattern: {profile.latestOperational.archetype}</Text>
            ) : null}
            {profile.latestOperational.neighbors ? (
              <Text tone="secondary" size="small">{profile.latestOperational.neighbors}</Text>
            ) : null}
          </CardBody>
        </Card>
        <Grid columns={4} gap={12}>
          <Stat value={String(snap.totalDays)} label="Days in history" tone="info" />
          <Stat value={String(snap.runDays)} label="Run days" tone="info" />
          <Stat value={String(snap.boneHighDays)} label="High running-load days" tone="warning" />
          <Stat value={String(snap.recoveryHighDays)} label="High recovery-risk days" tone="warning" />
        </Grid>
        <H2>High running-load days by year</H2>
        <Text tone="secondary" size="small">Source: athlete_bone_stress_scores.csv · count of high bone_stress_risk_level days</Text>
        <BarChart
          categories={charts.highBoneDaysByYear.categories}
          series={[{ name: 'High load days', data: charts.highBoneDaysByYear.values, tone: 'warning' }]}
          height={220}
          valueSuffix=""
        />
        <H2>What triggers high-load alerts</H2>
        <Text tone="secondary" size="small">Top reasons on high bone-stress days</Text>
        <PieChart
          data={charts.highDayReasons.labels.map((label, idx) => ({
            label,
            value: charts.highDayReasons.values[idx],
            tone: idx === 0 ? 'warning' : 'neutral',
          }))}
          donut
          size={220}
        />
        <Text tone="secondary" size="small">{profile.spring2024Note}</Text>
      </Stack>
    );
  }

  if (section === 'strengths') {
    return (
      <Stack gap={16}>
        <Text>
          These are patterns where your data suggests resilience — not immunity from injury, but areas where load and
          recovery have stayed aligned more often.
        </Text>
        <BulletCards items={profile.strengths} tone="success" />
      </Stack>
    );
  }

  if (section === 'risks') {
    return (
      <Stack gap={16}>
        <Text>
          Recurring ways monitoring flags you — usually about ramp rate, repeated patterns, or learned-state strain
          that rules alone do not capture.
        </Text>
        <BulletCards items={profile.weaknesses} tone="warning" />
      </Stack>
    );
  }

  if (section === 'windows') {
    return (
      <Stack gap={16}>
        <H2>Running-load blocks</H2>
        <Text tone="secondary" size="small">Source: athlete_bone_stress_periods.csv · plain-language summaries</Text>
        <Table
          headers={['Start', 'End', 'Peak week', 'Pattern', 'What happened']}
          rows={profile.riskWindows.map((row) => [row.start, row.end, row.peakKm, row.pattern, row.summary])}
          striped
        />
        <H2>Recovery-risk blocks</H2>
        <Text tone="secondary" size="small">Source: athlete_risk_periods.csv · autonomic recovery lagging workload</Text>
        <Table
          headers={['Start', 'End', 'Dominant pattern']}
          rows={profile.recoveryWindows.map((row) => [row.start, row.end, row.pattern])}
          striped
        />
      </Stack>
    );
  }

  if (section === 'tracks') {
    return (
      <Stack gap={16}>
        <Callout tone="info" title="How these scores describe this athlete">
          This page is about your pattern, not generic score definitions. The main story is: you tolerate high volume
          when progression is controlled, but the system repeatedly flags sharp ramps, repeated high-load days, and a
          smaller set of learned-state strain days where the frontier model sees something beyond simple mileage.
        </Callout>
        <Grid columns={3} gap={12}>
          <Stat value="438" label="Literature high days" tone="warning" />
          <Stat value="580" label="Personal history high days" tone="warning" />
          <Stat value="226" label="Frontier high days" tone="danger" />
        </Grid>
        <Table
          headers={['Signal', 'What it says about you', 'Why it matters']}
          rows={[
            [
              'Literature rule score',
              'It flags 438 high days, but many high-volume weeks are still in ACWR sweet spot/elevated rather than danger-zone territory.',
              'Your risk is less about every big week being reckless and more about accumulated volume exposure plus repeated hard patterns.',
            ],
            [
              'Personal history score',
              'It flags 580 high days — 305 more than the literature track.',
              'You often ramp harder relative to your own baseline than objective rules alone suggest. This is the clearest signal for “too much too soon for you.”',
            ],
            [
              'Rules + personal load risk',
              'This is the practical load-management read: sustained high volume, progression, monotony, and hard sessions rolled together.',
              'Use it to decide whether to reduce mileage/intensity. It explains the training-load reason behind most alerts.',
            ],
            [
              'Accumulated frontier state',
              'It carries high states forward: 226 high days out of 2,792 scored frontier days.',
              'When it fires, the model sees unusual learned-state strain, negative readiness surprise, reference similarity, or recent carried strain — useful for hidden-strain checks, not just km counting.',
            ],
            [
              'Frontier-integrated risk',
              'This should be the headline score when browsing days because it keeps the running-load explanation but adds the frontier signal.',
              'If integrated risk is high, inspect whether it came from load, accumulated frontier state, or both. The action differs depending on the source.',
            ],
            [
              'Recovery risk',
              'Recovery high days are much less common than running-load high days, and only a small number overlap with high running-load days.',
              'This suggests many load alerts are mechanical/progression concerns, while recovery alerts are separate moments to protect readiness and sleep.',
            ],
          ]}
          striped
        />
        <H2>What disagreement usually means for you</H2>
        <Grid columns={2} gap={12}>
          <Callout tone="warning" title="Personalized > literature">
            This is your most common useful disagreement. It means the load may not look extreme by general rules, but it
            is a sharp change against your own recent history. Treat these as ramp-rate warnings.
          </Callout>
          <Callout tone="info" title="Frontier high while rules are modest">
            This means learned-state strain has crossed high and may linger after the raw spike. Check sleep, HRV/readiness, recent cross-training, illness/stress,
            or whether the day resembles spring 2024 / other reference blocks.
          </Callout>
          <Callout tone="success" title="Literature high but personalized lower">
            You may have handled similar volume before, but the objective rules still see risk. Do not ignore it if the
            week includes hard sessions, monotony, or symptoms.
          </Callout>
          <Callout tone="danger" title="All tracks elevated">
            This is the strongest convergence signal. For this athlete, it usually means volume/progression plus learned
            state are aligned enough to justify backing off.
          </Callout>
        </Grid>
        <H2>Practical reading order</H2>
        <Table
          headers={['Step', 'Question to ask', 'Why']}
          rows={[
            ['1', 'Is Frontier-integrated risk high?', 'Start with the headline score because it reflects both normal load logic and the model.'],
            ['2', 'Is Rules + personal load risk high?', 'If yes, the issue is likely training-load management: volume, progression, monotony, or intensity.'],
            ['3', 'Is Accumulated frontier state high?', 'If yes, look for hidden strain or state similarity that mileage alone does not explain.'],
            ['4', 'Is Recovery risk high?', 'If yes, protect readiness before adding intensity, even if running load looks manageable.'],
          ]}
          striped
        />
      </Stack>
    );
  }

  return (
    <Stack gap={16}>
      <Text>Practical adjustments based on your dominant alert patterns — not generic training advice.</Text>
      {profile.recommendations.map((rec) => (
        <Callout
          key={rec.action}
          tone={rec.priority === 'high' ? 'warning' : rec.priority === 'medium' ? 'info' : 'success'}
          title={rec.action}
        >
          {rec.why}
        </Callout>
      ))}
      <CollapsibleSection title="Regenerate this profile" count={1}>
        <Text size="small">
          <Code>.venv/bin/python scripts/generate_athlete_profile.py</Code>
        </Text>
      </CollapsibleSection>
    </Stack>
  );
}

export default function AthleteProfile() {
  const [active] = useCanvasState<SectionId>('profileSection', 'overview');
  return (
    <Stack gap={20}>
      <Stack gap={8}>
        <H1>Athlete profile</H1>
        <Text>
          Interpretable summary of your training strengths, risk patterns, and what to adjust — derived from {
            profile.snapshot.dateStart
          } 
          to {profile.snapshot.dateEnd} Garmin data.
        </Text>
        <Text tone="secondary" size="small">
          Regenerate after new exports with generate_athlete_profile.py
        </Text>
      </Stack>
      <SectionNav />
      <Divider />
      <ActiveSection section={active} />
    </Stack>
  );
}
