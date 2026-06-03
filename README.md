# CS153 Athlete State Lab

An end-to-end wearable-data system that turns Garmin activity and wellness exports into interpretable athlete-state monitoring, learned frontier signals, and actionable training feedback.

## Built artifact

This project implements a complete Garmin-to-dashboard pipeline rather than only a model notebook. It includes data ingestion and validation, daily feature engineering, baseline readiness models, supervised and masked-pretrained TCN sequence models, embedding novelty analysis, athlete-specific risk scoring, retrospective evaluation scripts, generated React dashboard pages, a static deployed demo, and a local-only coaching API. The final artifact is usable as an interactive web app for reviewing training state, score equations, daily recommendations, date-level explanations, and evaluation results.


Note: The README is a submission overview and reproducibility guide. The deployed app is the primary way to review the full artifact: it includes the project overview, methods/results, score equations, athlete profile, daily briefing, date explorer, bone-stress periods, frontier outcomes, ingestion validation, and static coaching examples.

## What it does

Athlete State Lab ingests multi-year Garmin exports and builds a local web application for exploring training state, recovery risk, and bone-stress-oriented running-load patterns.

The primary risk score system combines four layers:

1. **Literature rule score** — interpretable sports-science-style load rules such as workload ratio, speed/intensity bands, monotony, strain, and progression.
2. **Personal history score** — percentile scoring against this athlete’s own historical running patterns.
3. **Accumulated frontier state** — a learned TCN/embedding signal that jumps on frontier strain spikes and decays based on subsequent load/recovery context.
4. **Frontier-integrated risk** — headline score blending interpretable load logic with the learned frontier model.

It also includes a separate **recovery risk** track using readiness, HRV, sleep/body battery, insufficient rest, and under-recovered training context.

## Why this matters

Wearable dashboards often show many raw metrics but do not explain what matters, why it matters, or what to do next. This project tries to bridge that gap and consolidate things by creating an athlete-specific monitoring system that can answer questions like:

- Is this day risky or just different?
- Is the alert caused by running volume, progression, intensity, recovery strain, or the learned model?
- Does this day resemble previous concerning blocks?
- What would be a reasonable training adjustment?

I wanted to make something people could understand and respond to. With the coaching side they can even interect directly in a grounded way.

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
| Ridge regression | MAE `18.52`, RMSE `22.62`; linear tabular baseline |
| MLP | MAE `20.74`, RMSE `25.35`; nonlinear tabular baseline |
| Supervised TCN | MAE `14.01`, RMSE `17.12` |
| Masked-pretrained TCN | MAE `12.26`, RMSE `15.31` |

Monitoring evidence:

| Metric | Count |
|---|---:|
| Literature high days | `438` |
| Personalized high days | `580` |
| Combined operational high days | `784` |
| Frontier high days | `226 / 2,792` |
| All-agree days | `1,027` |
| Frontier high while literature not high | `172` |

Retrospective reference checks:

- Before the spring 2024 bone-stress reference window, accumulated frontier high appeared with `50` days lead and all-track agreement appeared with `52` days lead.

These checks are retrospective validation aids. Event/reference dates are not used by the scoring algorithm.

## Local web app

Static deployed demo:

```text
https://cs-153-athlete-state.vercel.app
```

The Vercel deployment is a static frontend demo. It includes the generated coaching examples, but not the live coach API route; the live coach remains available only when running the backend locally.

The local app includes:

- **Project overview** — system summary and score explanations
- **Methods & results** — technical summary and model results
- **Score equations** — compact formulas for the scoring/model outputs
- **Evaluation & reproducibility** — evidence, limitations, and reproduction commands
- **Athlete profile** — strengths, risk patterns, and athlete-specific score interpretation
- **Daily briefing** — latest-day training recommendation
- **Date explorer** — searchable day-by-day score and explanation UI
- **Bone stress periods** — detected high-load running blocks
- **Frontier outcomes** — retrospective reference-window evaluation
- **Ingestion validation** — data coverage and validation summary
- **Coaching QA** — static coaching question-and-answer examples
- **Coach live** — API-backed coaching interface available only in local development

## Setup

### Python backend

From the repo root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If using the live coach API, set an OpenAI key:

```bash
export OPENAI_API_KEY=your_key_here
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

Generated canvas scripts update local UI artifacts. After regeneration, review the relevant page in the frontend before submission.

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
- `src/frontier_monitoring.py` — frontier strain, accumulated frontier state, and integrated score logic
- `scripts/score_athlete_risk.py` — risk scoring and bone-stress running-load scores
- `src/coach_api.py` — live local coaching API
- `web/src/App.tsx` — local UI routes

## Submission docs

- `README.md` — main project overview, setup, results, and reproducibility guide
- `SCIENTIFIC_RATIONALE.md` — literature sources and rationale behind the scoring design
- `AI_USE_DISCLOSURE.md` — honest disclosure of AI assistance, human decisions, sources, and collaborators

## Process and AI Use

This project was built with extensive AI coding assistance. See `AI_USE_DISCLOSURE.md` for the full disclosure of what AI helped with, what decisions and data came from me, and how sources/collaborators are credited.

## Limitations

- Single-athlete retrospective data.
- Not a clinical injury prediction model.
- Garmin readiness exists only for a subset of days.
- Frontier thresholds are useful monitoring heuristics, not medically validated cutoffs.
- Some outputs depend on private Garmin exports that are intentionally not committed.
- Retrospective reference periods help evaluate plausibility but do not prove prospective generalization.
