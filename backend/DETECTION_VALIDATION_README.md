# NetGuard: Weighted XGBoost V2 development-validation replay

1. Extract the ZIP into the root of `Network-Attack-Forecasting-Project-main`.
2. In VS Code terminal, activate `.venv312` (`source .venv312/bin/activate`).
3. Run from the project root:

```bash
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 PYTHONUNBUFFERED=1 python -u backend/validate_detection_train_split.py --download
```

The script downloads the notebook's pinned copy of the **UNSW-NB15 training CSV only** from Hugging Face if it isn't already cached. It checks the original file SHA-256 hash before using it. Requires internet for first run; the pinned external URL might become unavailable. It does not download or read the official TEST partition.

If you already have the **exact** original TRAIN CSV on your Mac, you can run without downloading:

```bash
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 python -u backend/validate_detection_train_split.py --train-file /full/path/to/UNSW_NB15_training-set.csv
```

The script reconstructs the original group-aware development split, loads the existing checkpoint and fitted preprocessor, and calculates the 10-class classification metrics and derived binary attack detection metrics. It neither fits preprocessing nor retrains. It writes `backend/model_release/detection_validation_v1.json`.

The training CSV is ~large; **do not commit `backend/validation_data/*.csv` or raw data to GitHub**. For local ignore rules, add `/backend/validation_data/` to your root `.gitignore`.

For context, reported weighted-XGBoost metrics on that same development split were: accuracy 0.816760, macro F1 0.643074, balanced accuracy 0.655136 and weighted F1 0.823379. This is a reused development split, NOT an independent final test or a real-world validation.
