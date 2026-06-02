import {
  Callout,
  CollapsibleSection,
  H1,
  H2,
  H3,
  Stack,
  Table,
  Text,
} from 'cursor/canvas';

const payload = {
  "model": "anthropic/claude-3.5-haiku",
  "entries": [
    {
      "date": "2026-05-15",
      "tier": "watch",
      "agreement": "all_agree",
      "context": {
        "date": "2026-05-15",
        "operational_alert_tier": "watch",
        "operational_alert_label": "Watch",
        "monitoring_signal_agreement": "all_agree",
        "literature_score": 60.0,
        "personalized_score": 56.864714128358024,
        "frontier_score": 45.27953819345989,
        "combined_score": 58.432357064179016,
        "dominant_reason": "sustained high running volume",
        "run7_km": 71.5,
        "accumulated_state": 70.05251245172485,
        "counterfactual_hint": "Sustained volume is the driver (~72 km/week). A recovery week at 50\u201360% of recent weekly km would reduce accumulated load.",
        "whatif_best_scenario": "If 7-day running volume were ~15% lower (61 vs 72 km/week), literature score would move 60 \u2192 60 (+0).",
        "reference_archetype": "Bone stress injury (spring 2024)",
        "embedding_neighbors": "Latent state resembles 2024-01-06, 2025-11-08, 2026-05-02.",
        "frontier_attribution": "Top latent-state drivers: fitness vo2MaxValue, Fatigue duration, hiking max hr, impact weighted distance m, hiking activity count.",
        "frontier_drivers": "fitness vo2MaxValue (2.650); Fatigue duration (0.615); hiking max hr (0.541); impact weighted distance m (0.439); hiking activity count (0.372)",
        "period_context": "Sustained elevated bone-stress load from 2026-04-22 to 2026-05-08 (17 calendar days). Accumulated bone-stress state peaked at 75 with 13 high day(s). Dominant pattern: sustained high running volume. Peak 7-day running total 109 km.",
        "scientific_rationale_excerpt": "# Scientific Rationale For Athlete-State Risk Scoring\n\n## Purpose\n\nThis document summarizes the scientific ideas used to ground the project's athlete-state risk scoring layer. The goal is not to claim that the system can diagnose injury or precisely predict injury. Instead, the goal is to build a defensible monitoring framework that combines:\n\n- recent workload\n- sport-specific stress\n- recovery markers\n- longitudinal rest/strain patterns\n- learned athlete-state embeddings\n\nThe core interpretation is:\n\n> A day is not risky just because it is different from history. A day becomes more concerning when the athlete appears under-recovered relative to the workload they recently absorbed or the workload they are about to perform.\n\n## 1. Training Load, Acute:Chronic Workload, And Workload Spikes\n\nTraining-load monitoring is commonly used to reason about whether an athlete is prepared for recent stress. Acute:chronic workload ratio (ACWR) compares recent workload against longer-term workload. In simple terms, the acute period estimates what the athlete recently did, while the chronic period estimates what the athlete has been prepared for.\n\nThe evidence is mixed. Systematic reviews suggest ACWR may be related to injury risk in some contexts, but the relationship varies substantially across sports, populations, workload definitions, and calculation methods. This means ACWR should be used as one feature in a broader monitoring system, not as a standalone injury predictor.\n\nRelevant points from the literature:\n\n- Maupin et al. reviewed ACWR and injury-risk studies and concluded that external and internal workload ratios may be related to injury risk, but findings are highly variable and ACWR methods need standardization before being used confidently as injury-prevention tools [1].\n- Griffin et al. found support for ACWR as part of a broader multifactorial monitoring system, while emphasizing that time windows, workload variables, and model choice depend on sport context [2].\n- Workload can be separated into external load, such as distance and duration, and internal load, such as heart-rate response or perceived effort. The same external workload may produce different internal responses depending on athlete readiness and fatigue state [1].\n\nHow this project uses it:\n\n- We treat prior-day and recent 3-7 day workload as risk contributors.\n- We do not treat high workload alone as automatically risky.\n- Workload becomes more meaningful when paired with poor recovery marke"
      },
      "answer_markdown": null,
      "status": "error",
      "error": "OpenRouter request failed (401): {\"error\":{\"message\":\"Missing Authentication header\",\"code\":401}}"
    },
    {
      "date": "2026-05-14",
      "tier": "watch",
      "agreement": "personalized_frontier_agree",
      "context": {
        "date": "2026-05-14",
        "operational_alert_tier": "watch",
        "operational_alert_label": "Watch",
        "monitoring_signal_agreement": "personalized_frontier_agree",
        "literature_score": 76.0,
        "personalized_score": 59.69953563560759,
        "frontier_score": 57.5593817425797,
        "combined_score": 67.8497678178038,
        "dominant_reason": "sustained high running volume",
        "run7_km": 80.1,
        "accumulated_state": 70.54980961714416,
        "counterfactual_hint": "Sustained volume is the driver (~80 km/week). A recovery week at 50\u201360% of recent weekly km would reduce accumulated load.",
        "whatif_best_scenario": null,
        "reference_archetype": "Bone stress injury (spring 2024)",
        "embedding_neighbors": "Latent state resembles 2026-03-20, 2026-05-01, 2026-04-03.",
        "frontier_attribution": null,
        "frontier_drivers": null,
        "period_context": "Sustained elevated bone-stress load from 2026-04-22 to 2026-05-08 (17 calendar days). Accumulated bone-stress state peaked at 75 with 13 high day(s). Dominant pattern: sustained high running volume. Peak 7-day running total 109 km.",
        "scientific_rationale_excerpt": "# Scientific Rationale For Athlete-State Risk Scoring\n\n## Purpose\n\nThis document summarizes the scientific ideas used to ground the project's athlete-state risk scoring layer. The goal is not to claim that the system can diagnose injury or precisely predict injury. Instead, the goal is to build a defensible monitoring framework that combines:\n\n- recent workload\n- sport-specific stress\n- recovery markers\n- longitudinal rest/strain patterns\n- learned athlete-state embeddings\n\nThe core interpretation is:\n\n> A day is not risky just because it is different from history. A day becomes more concerning when the athlete appears under-recovered relative to the workload they recently absorbed or the workload they are about to perform.\n\n## 1. Training Load, Acute:Chronic Workload, And Workload Spikes\n\nTraining-load monitoring is commonly used to reason about whether an athlete is prepared for recent stress. Acute:chronic workload ratio (ACWR) compares recent workload against longer-term workload. In simple terms, the acute period estimates what the athlete recently did, while the chronic period estimates what the athlete has been prepared for.\n\nThe evidence is mixed. Systematic reviews suggest ACWR may be related to injury risk in some contexts, but the relationship varies substantially across sports, populations, workload definitions, and calculation methods. This means ACWR should be used as one feature in a broader monitoring system, not as a standalone injury predictor.\n\nRelevant points from the literature:\n\n- Maupin et al. reviewed ACWR and injury-risk studies and concluded that external and internal workload ratios may be related to injury risk, but findings are highly variable and ACWR methods need standardization before being used confidently as injury-prevention tools [1].\n- Griffin et al. found support for ACWR as part of a broader multifactorial monitoring system, while emphasizing that time windows, workload variables, and model choice depend on sport context [2].\n- Workload can be separated into external load, such as distance and duration, and internal load, such as heart-rate response or perceived effort. The same external workload may produce different internal responses depending on athlete readiness and fatigue state [1].\n\nHow this project uses it:\n\n- We treat prior-day and recent 3-7 day workload as risk contributors.\n- We do not treat high workload alone as automatically risky.\n- Workload becomes more meaningful when paired with poor recovery marke"
      },
      "answer_markdown": null,
      "status": "error",
      "error": "OpenRouter request failed (401): {\"error\":{\"message\":\"Missing Authentication header\",\"code\":401}}"
    },
    {
      "date": "2026-05-13",
      "tier": "watch",
      "agreement": "all_agree",
      "context": {
        "date": "2026-05-13",
        "operational_alert_tier": "watch",
        "operational_alert_label": "Watch",
        "monitoring_signal_agreement": "all_agree",
        "literature_score": 60.0,
        "personalized_score": 54.63221428571428,
        "frontier_score": 65.27510112829032,
        "combined_score": 57.316107142857135,
        "dominant_reason": "sustained high running volume",
        "run7_km": 76.6,
        "accumulated_state": 70.91733200464307,
        "counterfactual_hint": "Sustained volume is the driver (~77 km/week). A recovery week at 50\u201360% of recent weekly km would reduce accumulated load.",
        "whatif_best_scenario": null,
        "reference_archetype": "Bone stress injury (spring 2024)",
        "embedding_neighbors": "Latent state resembles 2024-07-06, 2026-02-11, 2026-03-19.",
        "frontier_attribution": "Top latent-state drivers: fitness vo2MaxValue, impact weighted distance m, Fatigue duration, Impact duration, hiking max hr.",
        "frontier_drivers": "fitness vo2MaxValue (2.661); impact weighted distance m (0.514); Fatigue duration (0.435); Impact duration (0.427); hiking max hr (0.385)",
        "period_context": "Sustained elevated bone-stress load from 2026-04-22 to 2026-05-08 (17 calendar days). Accumulated bone-stress state peaked at 75 with 13 high day(s). Dominant pattern: sustained high running volume. Peak 7-day running total 109 km.",
        "scientific_rationale_excerpt": "# Scientific Rationale For Athlete-State Risk Scoring\n\n## Purpose\n\nThis document summarizes the scientific ideas used to ground the project's athlete-state risk scoring layer. The goal is not to claim that the system can diagnose injury or precisely predict injury. Instead, the goal is to build a defensible monitoring framework that combines:\n\n- recent workload\n- sport-specific stress\n- recovery markers\n- longitudinal rest/strain patterns\n- learned athlete-state embeddings\n\nThe core interpretation is:\n\n> A day is not risky just because it is different from history. A day becomes more concerning when the athlete appears under-recovered relative to the workload they recently absorbed or the workload they are about to perform.\n\n## 1. Training Load, Acute:Chronic Workload, And Workload Spikes\n\nTraining-load monitoring is commonly used to reason about whether an athlete is prepared for recent stress. Acute:chronic workload ratio (ACWR) compares recent workload against longer-term workload. In simple terms, the acute period estimates what the athlete recently did, while the chronic period estimates what the athlete has been prepared for.\n\nThe evidence is mixed. Systematic reviews suggest ACWR may be related to injury risk in some contexts, but the relationship varies substantially across sports, populations, workload definitions, and calculation methods. This means ACWR should be used as one feature in a broader monitoring system, not as a standalone injury predictor.\n\nRelevant points from the literature:\n\n- Maupin et al. reviewed ACWR and injury-risk studies and concluded that external and internal workload ratios may be related to injury risk, but findings are highly variable and ACWR methods need standardization before being used confidently as injury-prevention tools [1].\n- Griffin et al. found support for ACWR as part of a broader multifactorial monitoring system, while emphasizing that time windows, workload variables, and model choice depend on sport context [2].\n- Workload can be separated into external load, such as distance and duration, and internal load, such as heart-rate response or perceived effort. The same external workload may produce different internal responses depending on athlete readiness and fatigue state [1].\n\nHow this project uses it:\n\n- We treat prior-day and recent 3-7 day workload as risk contributors.\n- We do not treat high workload alone as automatically risky.\n- Workload becomes more meaningful when paired with poor recovery marke"
      },
      "answer_markdown": null,
      "status": "error",
      "error": "OpenRouter request failed (401): {\"error\":{\"message\":\"Missing Authentication header\",\"code\":401}}"
    },
    {
      "date": "2026-05-12",
      "tier": "watch",
      "agreement": "literature_personalized_agree_frontier_differs",
      "context": {
        "date": "2026-05-12",
        "operational_alert_tier": "watch",
        "operational_alert_label": "Watch",
        "monitoring_signal_agreement": "literature_personalized_agree_frontier_differs",
        "literature_score": 60.0,
        "personalized_score": 51.13032142857143,
        "frontier_score": 28.843431278508955,
        "combined_score": 55.56516071428571,
        "dominant_reason": "sustained high running volume",
        "run7_km": 68.6,
        "accumulated_state": 71.93136954984324,
        "counterfactual_hint": "Sustained volume is the driver (~69 km/week). A recovery week at 50\u201360% of recent weekly km would reduce accumulated load.",
        "whatif_best_scenario": null,
        "reference_archetype": "Feb\u2013Mar 2025 bike-heavy running ramp",
        "embedding_neighbors": "Latent state resembles 2026-04-01, 2025-11-04, 2026-03-30.",
        "frontier_attribution": "Top latent-state drivers: fitness vo2MaxValue, hiking max hr, impact weighted distance m, Fatigue duration, hiking activity count.",
        "frontier_drivers": "fitness vo2MaxValue (2.515); hiking max hr (0.542); impact weighted distance m (0.489); Fatigue duration (0.485); hiking activity count (0.357)",
        "period_context": "Sustained elevated bone-stress load from 2026-04-22 to 2026-05-08 (17 calendar days). Accumulated bone-stress state peaked at 75 with 13 high day(s). Dominant pattern: sustained high running volume. Peak 7-day running total 109 km.",
        "scientific_rationale_excerpt": "# Scientific Rationale For Athlete-State Risk Scoring\n\n## Purpose\n\nThis document summarizes the scientific ideas used to ground the project's athlete-state risk scoring layer. The goal is not to claim that the system can diagnose injury or precisely predict injury. Instead, the goal is to build a defensible monitoring framework that combines:\n\n- recent workload\n- sport-specific stress\n- recovery markers\n- longitudinal rest/strain patterns\n- learned athlete-state embeddings\n\nThe core interpretation is:\n\n> A day is not risky just because it is different from history. A day becomes more concerning when the athlete appears under-recovered relative to the workload they recently absorbed or the workload they are about to perform.\n\n## 1. Training Load, Acute:Chronic Workload, And Workload Spikes\n\nTraining-load monitoring is commonly used to reason about whether an athlete is prepared for recent stress. Acute:chronic workload ratio (ACWR) compares recent workload against longer-term workload. In simple terms, the acute period estimates what the athlete recently did, while the chronic period estimates what the athlete has been prepared for.\n\nThe evidence is mixed. Systematic reviews suggest ACWR may be related to injury risk in some contexts, but the relationship varies substantially across sports, populations, workload definitions, and calculation methods. This means ACWR should be used as one feature in a broader monitoring system, not as a standalone injury predictor.\n\nRelevant points from the literature:\n\n- Maupin et al. reviewed ACWR and injury-risk studies and concluded that external and internal workload ratios may be related to injury risk, but findings are highly variable and ACWR methods need standardization before being used confidently as injury-prevention tools [1].\n- Griffin et al. found support for ACWR as part of a broader multifactorial monitoring system, while emphasizing that time windows, workload variables, and model choice depend on sport context [2].\n- Workload can be separated into external load, such as distance and duration, and internal load, such as heart-rate response or perceived effort. The same external workload may produce different internal responses depending on athlete readiness and fatigue state [1].\n\nHow this project uses it:\n\n- We treat prior-day and recent 3-7 day workload as risk contributors.\n- We do not treat high workload alone as automatically risky.\n- Workload becomes more meaningful when paired with poor recovery marke"
      },
      "answer_markdown": null,
      "status": "error",
      "error": "OpenRouter request failed (401): {\"error\":{\"message\":\"Missing Authentication header\",\"code\":401}}"
    },
    {
      "date": "2026-05-11",
      "tier": "watch",
      "agreement": "literature_personalized_agree_frontier_differs",
      "context": {
        "date": "2026-05-11",
        "operational_alert_tier": "watch",
        "operational_alert_label": "Watch",
        "monitoring_signal_agreement": "literature_personalized_agree_frontier_differs",
        "literature_score": 60.0,
        "personalized_score": 63.7120226538398,
        "frontier_score": 38.29024903654368,
        "combined_score": 63.7120226538398,
        "dominant_reason": "sustained high running volume",
        "run7_km": 85.7,
        "accumulated_state": 73.48197399511815,
        "counterfactual_hint": "Sustained volume is the driver (~86 km/week). A recovery week at 50\u201360% of recent weekly km would reduce accumulated load.",
        "whatif_best_scenario": null,
        "reference_archetype": "Feb\u2013Mar 2025 bike-heavy running ramp",
        "embedding_neighbors": "Latent state resembles 2025-05-16, 2024-03-28, 2026-04-01.",
        "frontier_attribution": "Top latent-state drivers: fitness vo2MaxValue, impact weighted distance m, hiking max hr, Fatigue duration, hiking activity count.",
        "frontier_drivers": "fitness vo2MaxValue (2.581); impact weighted distance m (0.584); hiking max hr (0.502); Fatigue duration (0.441); hiking activity count (0.385)",
        "period_context": "Sustained elevated bone-stress load from 2026-04-22 to 2026-05-08 (17 calendar days). Accumulated bone-stress state peaked at 75 with 13 high day(s). Dominant pattern: sustained high running volume. Peak 7-day running total 109 km.",
        "scientific_rationale_excerpt": "# Scientific Rationale For Athlete-State Risk Scoring\n\n## Purpose\n\nThis document summarizes the scientific ideas used to ground the project's athlete-state risk scoring layer. The goal is not to claim that the system can diagnose injury or precisely predict injury. Instead, the goal is to build a defensible monitoring framework that combines:\n\n- recent workload\n- sport-specific stress\n- recovery markers\n- longitudinal rest/strain patterns\n- learned athlete-state embeddings\n\nThe core interpretation is:\n\n> A day is not risky just because it is different from history. A day becomes more concerning when the athlete appears under-recovered relative to the workload they recently absorbed or the workload they are about to perform.\n\n## 1. Training Load, Acute:Chronic Workload, And Workload Spikes\n\nTraining-load monitoring is commonly used to reason about whether an athlete is prepared for recent stress. Acute:chronic workload ratio (ACWR) compares recent workload against longer-term workload. In simple terms, the acute period estimates what the athlete recently did, while the chronic period estimates what the athlete has been prepared for.\n\nThe evidence is mixed. Systematic reviews suggest ACWR may be related to injury risk in some contexts, but the relationship varies substantially across sports, populations, workload definitions, and calculation methods. This means ACWR should be used as one feature in a broader monitoring system, not as a standalone injury predictor.\n\nRelevant points from the literature:\n\n- Maupin et al. reviewed ACWR and injury-risk studies and concluded that external and internal workload ratios may be related to injury risk, but findings are highly variable and ACWR methods need standardization before being used confidently as injury-prevention tools [1].\n- Griffin et al. found support for ACWR as part of a broader multifactorial monitoring system, while emphasizing that time windows, workload variables, and model choice depend on sport context [2].\n- Workload can be separated into external load, such as distance and duration, and internal load, such as heart-rate response or perceived effort. The same external workload may produce different internal responses depending on athlete readiness and fatigue state [1].\n\nHow this project uses it:\n\n- We treat prior-day and recent 3-7 day workload as risk contributors.\n- We do not treat high workload alone as automatically risky.\n- Workload becomes more meaningful when paired with poor recovery marke"
      },
      "answer_markdown": null,
      "status": "error",
      "error": "OpenRouter request failed (401): {\"error\":{\"message\":\"Missing Authentication header\",\"code\":401}}"
    }
  ]
} as const;

function AnswerText({ content }: { content: string }) {
  const lines = content.split('\n');
  return (
    <Stack gap={6}>
      {lines.map((line, idx) => {
        const trimmed = line.trim();
        if (!trimmed) return null;
        if (trimmed.startsWith('### ')) {
          return <H3 key={idx}>{trimmed.slice(4)}</H3>;
        }
        if (trimmed.startsWith('- ')) {
          return <Text key={idx}>• {trimmed.slice(2)}</Text>;
        }
        if (trimmed.startsWith('**') && trimmed.includes('**', 2)) {
          const end = trimmed.indexOf('**', 2);
          const bold = trimmed.slice(2, end);
          const rest = trimmed.slice(end + 2).replace(/^:\s*/, '');
          return (
            <Text key={idx} weight="semibold">
              {bold}{rest ? `: ${rest}` : ''}
            </Text>
          );
        }
        return <Text key={idx}>{trimmed}</Text>;
      })}
    </Stack>
  );
}

export default function CoachingQa() {
  const latest = payload.entries[0];

  return (
    <Stack gap={20}>
      <Stack gap={8}>
        <H1>Coaching Q&amp;A</H1>
        <Text>
          Grounded answers for recent flagged days — generated from structured scores, attribution, and scientific rationale.
        </Text>
        <Text tone="secondary" size="small">
          Model: {payload.model} · requires OPENROUTER_API_KEY · regenerate with generate_coaching_qa.py
        </Text>
      </Stack>

      {latest && latest.status === 'ok' ? (
        <Callout tone="info" title={`${latest.date} · ${String(latest.tier).replace(/_/g, ' ')} · ${String(latest.agreement).replace(/_/g, ' ')}`}>
          <AnswerText content={latest.answer_markdown || ''} />
        </Callout>
      ) : (
        <Callout tone="warning" title="No coaching answer yet">
          {latest?.error || 'Set OPENROUTER_API_KEY and rerun generate_coaching_qa.py.'}
        </Callout>
      )}

      <H2>Recent flagged days</H2>
      <Table
        headers={['Date', 'Tier', 'Agreement', 'Status']}
        rows={payload.entries.map((entry) => [
          entry.date,
          String(entry.tier).replace(/_/g, ' '),
          String(entry.agreement).replace(/_/g, ' '),
          entry.status,
        ])}
        striped
      />

      <CollapsibleSection title="All answers" count={payload.entries.length}>
        <Stack gap={16}>
          {payload.entries.map((entry) => (
            <Stack key={entry.date} gap={8}>
              <H2>{entry.date} · {String(entry.tier).replace(/_/g, ' ')}</H2>
              {entry.status === 'ok' ? (
                <AnswerText content={entry.answer_markdown || ''} />
              ) : (
                <Text tone="secondary">{entry.error || 'No answer generated.'}</Text>
              )}
            </Stack>
          ))}
        </Stack>
      </CollapsibleSection>
    </Stack>
  );
}
