# CS153 Athlete State Lab

An end-to-end wearable-data system that turns Garmin activity and wellness exports into interpretable athlete-state monitoring, learned frontier signals, and actionable training feedback.

The project is built for the CS 153 “One-Person Frontier Lab” final project: one person using modern AI/developer tools to create a working product and research artifact from private real-world data.

## What it does

Athlete State Lab ingests multi-year Garmin exports and builds a local web application for exploring training state, recovery risk, and bone-stress-oriented running-load patterns.

The system combines four layers:

1. **Literature rule score** — interpretable sports-science-style load rules such as workload ratio, speed/intensity bands, monotony, strain, and progression.
2. **Personal history score** — percentile scoring against this athlete’s own historical running patterns.
3. **Model-only frontier strain** — a learned TCN/embedding signal using embedding novelty, readiness forecast error, and similarity to reference risky blocks.
4. **Frontier-integrated risk** — headline score blending interpretable load logic with the learned frontier model.

It also includes a separate **recovery risk** track using readiness, HRV, sleep/body battery, insufficient rest, and under-recovered training context.

## Why this matters

Wearable dashboards often show many raw metrics but do not explain what matters, why it matters, or what to do next. This project tries to bridge that gap by creating an athlete-specific monitoring system that can answer questions like:

- Is this day risky or just different?
- Is the alert caused by running volume, progression, intensity, recovery strain, or the learned model?
- Does this day resemble previous concerning blocks?
- What would be a reasonable training adjustment?

This is not a medical diagnosis tool. It is a training-context and decision-support system.

## Current results

Dataset snapshot:

- Date range: `2018-08-26` to `2026-05-15`
- Daily rows: `2,820`
- Feature columns: about `305`
- Frontier-covered days: `2,792`
- Modeling target: next-day Garmin readiness score

Modeling evidence:

| Model | Result / role |
|---|---|
| Naive persistence | baseline sanity check |
| Ridge regression | linear tabular baseline |
| MLP | nonlinear tabular baseline |
| Supervised TCN | MAE `14.01`, RMSE `17.12` |
| Masked-pretrained TCN | MAE `12.26`, RMSE `15.31` |

Monitoring evidence:

| Metric | Count |
|---|---:|
| Literature high days | `438` |
| Personalized high days | `580` |
| Combined operational high days | `784` |
| Frontier high days | `190 / 2,792` |
| All-agree days | `667` |
| Frontier high while literature not high | `151` |

Retrospective reference checks:

- Before the spring 2024 bone-stress reference window, frontier high appeared with `52` days lead and all-track agreement appeared with `51` days lead.
- Before the Feb–Mar 2025 bike-heavy running ramp reference period, frontier/integrated high appeared with `56` days lead.

These checks are retrospective validation aids. Event/reference dates are not used by the scoring algorithm.

## Local web app

The local app includes:

- **Project overview** — system summary and score explanations
- **Methods & results** — CS 153-friendly technical summary and model results
- **Evaluation & reproducibility** — evidence, limitations, and reproduction commands
- **Athlete profile** — strengths, risk patterns, and athlete-specific score interpretation
- **Daily briefing** — latest-day training recommendation
- **Date explorer** — searchable day-by-day score and explanation UI
- **Bone stress periods** — detected high-load running blocks
- **Frontier outcomes** — retrospective reference-window evaluation
- **Ingestion validation** — data coverage and validation summary
- **Coaching QA / Coach live** — static and API-backed coaching question interface

## Setup

### Python backend

From the repo root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If using the live coach API, set an OpenRouter key:

```bash
export OPENROUTER_API_KEY=your_key_here
```

Run the backend:

```bash
python run_coach_api.py
```

Backend address:

```text
http://localhost:8000
```

### Frontend

In a second terminal:

```bash
cd web
npm install
npm run dev
```

Frontend address:

```text
http://localhost:5173
```

## Reproducing the analysis pipeline

The main workflow is:

```bash
python scripts/validate_daily_features.py
python scripts/build_timeseries_dataset.py
python scripts/run_baselines.py
python scripts/train_tcn.py
python scripts/pretrain_masked_tcn.py
python scripts/finetune_tcn_from_pretrained.py
python scripts/analyze_embeddings.py
python scripts/score_athlete_risk.py
python scripts/evaluate_frontier_outcomes.py
python scripts/compare_monitoring_signals.py
```

Regenerate local UI artifacts:

```bash
python scripts/generate_daily_briefing.py
python scripts/generate_date_explorer_canvas.py
python scripts/generate_bone_stress_periods_canvas.py
python scripts/generate_coaching_qa.py
python scripts/generate_athlete_profile.py
```

Important: some generated canvas files can overwrite custom UI improvements. If regenerating canvases, verify `canvases/date-explorer.canvas.tsx` and other hand-polished pages before final submission.

## Repository structure

```text
src/                     Core pipeline, API, scoring, modeling utilities
src/modeling/            TCN and pretraining model code
scripts/                 Reproducible analysis/training/generation scripts
config/                  Feature and outcome-event configuration
canvases/                Generated and hand-refined local UI pages
web/                     Vite/React frontend shell
outputs/analysis/        Generated summaries used by the UI
data/processed/          Processed daily feature snapshots
```

## Important files

- `src/garmin_pipeline.py` — Garmin ingestion and daily aggregation
- `scripts/build_timeseries_dataset.py` — chronological modeling windows
- `src/modeling/tcn.py` — TCN model architecture
- `scripts/pretrain_masked_tcn.py` — self-supervised masked reconstruction
- `scripts/finetune_tcn_from_pretrained.py` — readiness fine-tuning
- `src/frontier_monitoring.py` — frontier strain and integrated score logic
- `scripts/score_athlete_risk.py` — risk scoring and bone-stress running-load scores
- `src/coach_api.py` — live local coaching API
- `web/src/App.tsx` — local UI routes

## Limitations

- Single-athlete retrospective data.
- Not a clinical injury prediction model.
- Garmin readiness exists only for a subset of days.
- Frontier thresholds are useful monitoring heuristics, not medically validated cutoffs.
- Some outputs depend on private Garmin exports that are intentionally not committed.
- Retrospective reference periods help evaluate plausibility but do not prove prospective generalization.

## Suggested demo video structure

1. **Why build it?** Wearables produce too much raw data and too little interpretable training guidance.
2. **How it works.** Show ingestion → TCN embeddings → frontier score → Date Explorer / Athlete Profile.
3. **Evidence.** Show Methods & Results and Evaluation pages: model improvement, agreement counts, retrospective checks.
4. **Use cases.** Athlete self-monitoring, coaching review, training-load explanation, recovery-aware planning.
5. **What would come next.** Better prospective validation, multi-athlete evaluation, interactive counterfactual simulator, and safer deployment/data privacy controls.
