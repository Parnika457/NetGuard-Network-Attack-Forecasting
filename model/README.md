# NetGuard: Machine Learning and Research Models

This directory contains the selected research artifacts developed for
network attack detection and future attack forecasting.

## Directory Structure

- `artifacts/current_detection/`: flow-level attack classification
  checkpoints, supporting preprocessing files and model metadata.
- `artifacts/forecasting/`: temporal, competing-risk, boosted-tree
  and graph-based model checkpoints.
- `notebooks/`: research and training notebooks with execution
  outputs removed from the repository copies.
- `research_paper/`: approved publication figures, tables and
  the monochrome research architecture.
- `manifests/`: the original staging provenance and SHA-256 records.

See `ARTIFACT_INDEX.md` for the checkpoint names.

## Current Attack Detection

Saved models include the baseline XGBoost multiclass classifier,
weighted XGBoost, conflict-aware XGBoost, CatBoost, and a
DoS-versus-Exploits specialist.

This task operates on flow-level UNSW-NB15-derived features.

## Future Attack Forecasting

Saved models include single-layer and stacked/horizon LSTMs,
competing-risk LSTM and TCN, XGBoost V2 (H5 and H10), and
graph-based LSTM, GCN-LSTM, GAT-LSTM and node-aware variants.

The research forecasting experiments used Synthetic NAF v2
minute-level episodes derived from CIC-IDS2017 and UNSW-NB15.

## Model Compatibility

These are saved research artifacts, not a fully integrated
production inference service.

Neural checkpoints may require model-class definitions and
feature-processing logic from the training notebooks.
The current-detection and forecasting inputs are different.
The models must not be combined into a single predictor
without a verified input/output contract.

Some notebooks retain Colab/Drive-specific paths and need
portable path configuration before running elsewhere.

## Evaluation Scope

Reported results are development-validation results.
They are not independent official TEST-set results.

The repository does not claim that RAG explanations, backend
inference APIs, or live frontend model integration have been
implemented and verified.

## Provenance

See `manifests/model_bundle_manifest.json`.

Saved model file contents were copied without modification.
The original research data and checkpoints remain in Drive.
