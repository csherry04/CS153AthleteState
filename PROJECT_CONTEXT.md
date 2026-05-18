# Project

A Self-Supervised Model of Athlete State for Recovery Prediction and Training Decisions

# Goal

Build an end-to-end self-supervised machine learning system that learns a latent representation of athlete physiological state from longitudinal training and recovery data.

The system should:
- ingest Garmin export data
- identify relevant athlete/recovery files
- aggregate data into daily time-series features
- learn latent athlete state embeddings
- support anomaly detection
- forecast recovery
- simulate simple training recommendations

# Constraints

- prioritize robustness and modularity
- avoid overengineering
- focus on working MVP first
- use Python + PyTorch
- data may be incomplete and inconsistent
- handle missing fields gracefully

# Initial Priority

Build ingestion + preprocessing pipeline first.

DO NOT build advanced ML systems before data preprocessing works correctly.