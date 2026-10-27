# NetGuard frozen synthetic validation windows

This package contains a read-only forecasting validation script and the checksum-verified, unchanged `windows_W10_VALIDATION.npz` downloaded from the original `Synthetic_NAF_v2/release_candidate_corrected` Google Drive folder. It **does not** evaluate the separately trained current-attack XGBoost detector.

## Installation

1. Copy `backend/validate_forecast_windows.py` to your project's existing `backend/` folder, next to `netguard_models.py`.
2. Make a directory `backend/validation_data/` and copy `windows_W10_VALIDATION.npz` into it.
3. Activate your working Python 3.12 `.venv312` virtual environment.
4. From the repository root run:

```bash
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 PYTHONUNBUFFERED=1 python -u backend/validate_forecast_windows.py
```

The script evaluates all 18,839 synthetic validation windows, reports AP/ROC AUC/Brier for H5/H10/H15 for both LSTMs, plus competing-risk family and ETA metrics. It verifies the SHA-256 input dataset and saved model weights/scalers before inference. It saves a report at `backend/model_release/validation_windows_v1.json`.

For a quick environment check first, optionally use `--limit 1000` (subset results are not comparable to full validation metrics).

**Restrictions:** Do not substitute TEST data, retrain or recalibrate, or treat validation metrics as independently measured real-world accuracy. The provided dataset is simulated.

## Reference results from an independent local replay

The accompanying `reference_validation_metrics.json` records one full validation replay performed in a separate CPU environment using the **committed original checkpoint files** and unmodified validation data:

| Metric | Stacked LSTM V2 | Competing-risk LSTM |
|---|---:|---:|
| H5 AP | 0.761005 | 0.724838 |
| H10 AP | 0.906018 | 0.899137 |
| H15 AP | 0.935854 | 0.936059 |

Competing-risk model: onset-family accuracy 0.808889, macro F1 0.795823, conditional ETA MAE 2.536534 minutes (conditioned on actual onset windows). These match the saved research benchmark to rounding precision. Different CPU/library versions may cause tiny floating-point differences.
