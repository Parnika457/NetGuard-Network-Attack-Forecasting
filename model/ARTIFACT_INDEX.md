# NetGuard model artifact index

This directory contains selected saved research artifacts.
They were copied from Google Drive with SHA-256 verification.

## Current network attack detection

The current-attack models classify UNSW-NB15 network flows.
Binary attack scores can be derived from the Normal-class probability.

## Future attack forecasting

The forecasting models were evaluated on Synthetic NAF v2
minute-level episodes. H5/H10/H15 availability varies by model.

## Artifact locations

### `current_detection/xgboost_v1`
- `current_attack_xgboost.ubj`

### `current_detection/weighted_xgboost_v2`
- `weighted_xgboost.ubj`

### `current_detection/conflict_aware_xgboost`
- `conflict_aware_xgboost.ubj`

### `current_detection/catboost`
- `catboost_10class.cbm`

### `current_detection/dos_specialist`
- `dos_exploits_xgboost.ubj`

### `forecasting/single_lstm`
- `LSTM_V2_SINGLE_LAYER_STATE.pt`

### `forecasting/stacked_lstm`
- `LSTM_V2_MONOTONIC_HORIZON_STATE.pt`

### `forecasting/competing_risk_lstm`
- `LSTM_V2_CR_STATE.pt`

### `forecasting/competing_risk_tcn`
- `TCN_V2_CR_STATE.pt`

### `forecasting/xgboost_v2`
- `XGBoost_V2_FLAT140_H5.json`
- `XGBoost_V2_FLAT140_H10.json`

### `forecasting/graph_models/original_graph_lstm`
- `GRAPH_LSTM_STATE.pt`

### `forecasting/graph_models/optimized_graph_lstm`
- `GRAPH_LSTM_C02_OPTIMIZED_STATE.pt`

### `forecasting/graph_models/gcn_lstm`
- `GCN_LSTM_STATE.pt`

### `forecasting/graph_models/gat_lstm`
- `GAT_LSTM_STATE.pt`

### `forecasting/graph_models/node_aware_lstm`
- `NODE_LSTM_STATE.pt`

## Important deployment notes

- Model weights alone are not a complete inference service.
- Some checkpoints require model architecture definitions,
  external feature schemas, scalers or graph-construction code.
- Inference dependencies and package versions must be audited.
- Current-detection and forecasting data schemas are different.
- The specialist must not be assumed to share the main model's
  preprocessor without explicit verification.
- Development-validation scores are not independent TEST results.
- No live-network deployment is established by these artifacts.

## Provenance

See `manifests/model_bundle_manifest.json` for copied files
and their SHA-256 checksums.
