# Athlete State Modeling Project Overview

## What This Project Is

This project is an end-to-end wearable data system for learning an athlete's physiological state from Garmin exports. It ingests raw activity, wellness, sleep, training load, readiness, HRV, and heart-rate data; aggregates it into daily features; builds chronological time-series datasets; trains forecasting models; learns latent athlete-state embeddings; and analyzes unusual days.

The current modeling goal is next-day readiness prediction and interpretable latent state analysis.

For the sports-science rationale behind the current risk model and proposed preparedness-mismatch direction, see `SCIENTIFIC_RATIONALE.md`.

## Current Data Pipeline

The ingestion pipeline lives in `src/garmin_pipeline.py`.

It recursively scans Garmin export files and supports:

- FIT
- CSV
- JSON
- TCX
- XML

The pipeline standardizes parsed records into pandas dataframes, handles missing fields gracefully, deduplicates repeated activities that appear in multiple Garmin exports, aggregates activity-level data to daily summaries, and writes processed features to `data/processed/daily_features_with_fit_deduped.csv`.

The activity aggregation now also decomposes workload by sport family:

- running duration, distance, heart rate, and activity count
- cycling duration, distance, heart rate, and activity count
- hiking duration, distance, heart rate, and activity count
- impact-weighted duration and distance
- fatigue-weighted duration

Current processed feature snapshot:

- Date range: `2018-08-26` to `2026-05-15`
- Daily rows: `2,820`
- Feature columns: about `305`
- Modeling target: `readiness_score`

Private Garmin data and generated artifacts are intentionally ignored by git.

## Validation And Feature Preparation

Validation and modeling prep scripts were added under `scripts/`:

- `scripts/validate_daily_features.py`: missingness reports, summary statistics, date ranges, and plots.
- `scripts/build_timeseries_dataset.py`: chronological train/validation/test splits and 28-day sliding windows.
- `config/model_features.json`: selected modeling features, including 62 current daily inputs, target column, split fractions, TCN settings, and masked pretraining settings.

The dataset builder uses chronological splits and fits imputation/scaling only on training-period data to avoid leakage.

## Baseline Modeling

The baseline layer is implemented in `scripts/run_baselines.py`.

It evaluates:

- naive persistence
- Ridge regression
- small MLP

This gives a sanity-check benchmark before sequence modeling.

## Temporal Sequence Modeling

The supervised TCN is implemented in `src/modeling/tcn.py` and trained by `scripts/train_tcn.py`.

It uses a lightweight causal Temporal Convolutional Network over 28-day multivariate windows. The model predicts next-day readiness and exports a compact latent embedding from the penultimate layer.

Supervised TCN test performance after activity deduplication:

- MAE: `14.01`
- RMSE: `17.12`

Outputs are written to `outputs/modeling/tcn/`.

## Self-Supervised Representation Learning

Masked reconstruction pretraining was added to learn athlete-state embeddings without directly optimizing for readiness first.

Key files:

- `src/modeling/pretraining.py`
- `scripts/pretrain_masked_tcn.py`
- `scripts/finetune_tcn_from_pretrained.py`

The masked pretraining setup randomly masks observed values in each 28-day standardized input window. A TCN encoder plus lightweight reconstruction head predicts the original standardized values. Reconstruction loss is computed only on positions that were both originally observed and selected for masking.

After pretraining, the encoder weights are reused for readiness forecasting and embedding extraction.

Masked-pretrained fine-tuned TCN test performance after sport-specific feature expansion (62 daily inputs):

- MAE: `12.26`
- RMSE: `15.31`
- Pretraining validation reconstruction RMSE: `10.67`

This still improves over the supervised-only TCN on the same split (`14.01` MAE / `17.12` RMSE).

Outputs are written to:

- `outputs/modeling/masked_tcn/`
- `outputs/modeling/masked_tcn_finetuned/`
- `outputs/modeling/pretrained_embeddings.csv`

## Embedding And Anomaly Analysis

The embedding interpretation layer is implemented in `scripts/analyze_embeddings.py`.

It joins learned embeddings back to daily Garmin features and produces:

- top anomaly-score days
- readiness, load, HRV, resting HR, and activity context for each anomaly
- nearest previous normal embedding days
- anomaly report CSV
- anomaly score plots against load/readiness
- PCA plots colored by readiness, load, and date

Outputs are written to `outputs/analysis/`.

Top anomaly days after retraining on sport-specific inputs include:

- `2025-03-22`
- `2026-03-23`
- `2025-07-14`
- `2026-03-15`
- `2025-10-01`

## Risk-Oriented Scoring

The risk layer is implemented in `scripts/score_athlete_risk.py`.

It separates embedding novelty from actual recovery/training risk. This matters because an off day or easy day can be unusual without being risky. The risk score is therefore built from separate components:

- state novelty from the learned embedding
- recovery strain from readiness, HRV, resting HR, sleep, and body battery signals
- prior workload from previous-day and recent workload/duration/distance
- metabolic fatigue from recent workload plus fatigue-weighted sport duration
- tissue load from running/hiking-heavy impact-weighted workload
- preparedness mismatch when high workload demand appears alongside poor recovery
- rest/easy-day context so low activity does not become a warning by itself
- insufficient-rest signal over recent days

Outputs are written to:

- `outputs/analysis/athlete_risk_scores.csv`
- `outputs/analysis/top_risk_days.csv`
- `outputs/analysis/athlete_risk_summary.json`
- `outputs/analysis/risk_score_over_time.png`
- `outputs/analysis/prior_workload_vs_recovery_strain.png`
- `outputs/analysis/insufficient_rest_over_time.png`
- `outputs/analysis/novelty_vs_risk.png`
- `outputs/analysis/sport_specific_risk_components.png`

The intended interpretation is that a rest day is not risky unless recovery markers are also poor or recent workload suggests under-recovery. A hard bike ride, hard run, and off day can now contribute differently: cycling is treated more as metabolic fatigue, while running and hiking receive more tissue-load weight.

## Athlete-Facing Feedback Layer

The next interpretation layer is implemented in `scripts/generate_athlete_feedback.py`.

It converts both embedding anomalies and top risk days into readable athlete-facing summaries. The risk-focused feedback prioritizes days where recovery markers look poor relative to recent workload, rather than flagging low-activity days simply because they are different from training days.

Outputs are written to:

- `outputs/analysis/athlete_feedback.md`
- `outputs/analysis/athlete_feedback.csv`
- `outputs/analysis/athlete_feedback.json`
- `outputs/analysis/athlete_risk_feedback.md`
- `outputs/analysis/athlete_risk_feedback.csv`
- `outputs/analysis/athlete_risk_feedback.json`

This is currently deterministic and rule-based, which keeps it reproducible. A future LLM layer could use these structured outputs to generate more natural coaching-style explanations.

## Most Important Files

- `PROJECT_CONTEXT.md`: original goal and constraints.
- `PROJECT_OVERVIEW.md`: this summary.
- `src/garmin_pipeline.py`: ingestion and daily feature engineering.
- `src/modeling/dataset.py`: chronological time-series dataset builder.
- `src/modeling/tcn.py`: shared TCN encoder, supervised forecaster, and masked autoencoder.
- `src/modeling/pretraining.py`: masked reconstruction dataset helpers.
- `config/model_features.json`: modeling feature and training configuration.
- `scripts/train_tcn.py`: supervised TCN training.
- `scripts/pretrain_masked_tcn.py`: masked reconstruction pretraining.
- `scripts/finetune_tcn_from_pretrained.py`: readiness fine-tuning from pretrained encoder.
- `scripts/analyze_embeddings.py`: athlete-state embedding interpretation.
- `scripts/score_athlete_risk.py`: risk-oriented scoring that separates novelty, recovery strain, workload, sport-specific tissue/fatigue load, rest context, and insufficient rest.
- `scripts/generate_athlete_feedback.py`: athlete-facing explanations and suggested actions for anomaly days.

## How To Reproduce The Main Workflow

From the project root:

```bash
.venv/bin/python scripts/validate_daily_features.py
.venv/bin/python scripts/build_timeseries_dataset.py
.venv/bin/python scripts/run_baselines.py
.venv/bin/python scripts/train_tcn.py
.venv/bin/python scripts/pretrain_masked_tcn.py
.venv/bin/python scripts/finetune_tcn_from_pretrained.py
.venv/bin/python scripts/analyze_embeddings.py
.venv/bin/python scripts/score_athlete_risk.py
.venv/bin/python scripts/generate_athlete_feedback.py
```

The ingestion pipeline can be rerun if needed, but it should not be modified unless necessary.

## Current Interpretation

The project now has a full path from raw Garmin exports to learned latent athlete states. The strongest current result is that masked reconstruction pretraining improves downstream readiness forecasting compared with the supervised-only TCN. The anomaly analysis also makes the embeddings more interpretable by tying unusual latent states back to readiness, load, HRV, resting heart rate, activity metrics, and nearest prior normal days.

The next useful step is to connect these risk-focused explanations to a small interactive demo or LLM-assisted narrative layer, so the system can answer questions like "was this day risky or just different?", "was this more of a metabolic fatigue signal or tissue-load signal?", "what workload likely drove this recovery response?", and "has there been enough rest recently?"
