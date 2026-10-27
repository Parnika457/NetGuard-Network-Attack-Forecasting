"""Read-only NetGuard weighted-XGBoost V2 development-validation reproduction.

Uses the verified canonical UNSW-NB15 *TRAIN* partition only, reconstructs
Cell 6's exact StratifiedGroupKFold split, and compares the saved model's
metrics with the training notebook's published development metrics.

Does NOT fit, retrain, choose thresholds, access official TEST, or modify weights.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone

# The notebook fit its preprocessor with scikit-learn 1.6.1.
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, f1_score,
    precision_recall_fscore_support, average_precision_score,
)
from sklearn.model_selection import StratifiedGroupKFold
import xgboost as xgb

PROJECT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = PROJECT / 'model/artifacts/current_detection/weighted_xgboost_v2'
DATA_DIR = PROJECT / 'backend/validation_data'
DEFAULT_TRAIN = DATA_DIR / 'UNSW_NB15_training-set.csv'
REPORT = PROJECT / 'backend/model_release/detection_validation_v1.json'

# Exact source and checksum from Current_Attack_Detection.ipynb, Cell 5.
TRAIN_URL = (
    'https://huggingface.co/datasets/Mouwiya/UNSW-NB15/resolve/'
    '8ad6b19373f143086a66f52b0d6035a6959d83a9/'
    'UNSW_NB15_training-set.csv'
)
EXPECTED_TRAIN_SHA256 = 'bec7dd5ec88dc2a0ccc7a07879d338395ed7421750f675fd0339e07dfe0648fa'
EXPECTED_CLASS_COUNTS = {
    'Normal': 56000, 'Generic': 40000, 'Exploits': 33393,
    'Fuzzers': 18184, 'DoS': 12264, 'Reconnaissance': 10491,
    'Analysis': 2000, 'Backdoor': 1746, 'Shellcode': 1133, 'Worms': 130,
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fp:
        for b in iter(lambda: fp.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def ensure_verified_train(path: Path, download: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        if not download:
            raise FileNotFoundError(f'{path} not found; supply --download or --train-file /path/to/file')
        print('Downloading the revision-pinned TRAIN partition (not the TEST file)...', flush=True)
        tmp = path.with_suffix('.partial')
        try:
            request = urllib.request.Request(TRAIN_URL, headers={'User-Agent': 'NetGuard-validation-replay/1.0'})
            with urllib.request.urlopen(request, timeout=120) as src, tmp.open('wb') as dest:
                while True:
                    block = src.read(1024 * 1024)
                    if not block:
                        break
                    dest.write(block)
            if sha256(tmp) != EXPECTED_TRAIN_SHA256:
                raise RuntimeError('Downloaded TRAIN checksum mismatch; refusing to use this file')
            tmp.replace(path)
        finally:
            if tmp.exists():
                tmp.unlink()
    actual = sha256(path)
    if actual != EXPECTED_TRAIN_SHA256:
        raise RuntimeError(f'Canonical TRAIN checksum mismatch for {path}: {actual}')
    print(f'[PASS] Canonical TRAIN integrity: {actual}', flush=True)


def reconstruct_validation(df: pd.DataFrame, features):
    X = df[features].copy()
    y = df['attack_cat'].astype(str).str.strip()
    groups = pd.util.hash_pandas_object(X, index=False)
    overall = y.value_counts(normalize=True)
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    candidates = []
    for fold_id, (train_idx, val_idx) in enumerate(splitter.split(X, y, groups)):
        val_proportion = y.iloc[val_idx].value_counts(normalize=True).reindex(overall.index, fill_value=0)
        distribution_error = float((val_proportion - overall).abs().sum())
        size_error = abs(len(val_idx) / len(df) - 0.20)
        candidates.append((distribution_error + size_error, fold_id, train_idx, val_idx))
    _, selected, train_idx, val_idx = min(candidates, key=lambda x: x[0])
    if set(groups.iloc[train_idx].to_numpy()) & set(groups.iloc[val_idx].to_numpy()):
        raise RuntimeError('Feature-group leakage between fit and validation splits')
    if selected != 4 or len(train_idx) != 140174 or len(val_idx) != 35167:
        raise RuntimeError(f'Split mismatch: fold={selected}, train={len(train_idx)}, val={len(val_idx)}. Check pandas/scikit-learn versions.')
    print(f'[PASS] Original group-isolated split: fold={selected}, development train={len(train_idx):,}, validation={len(val_idx):,}', flush=True)
    return X.iloc[val_idx].copy(), y.iloc[val_idx].copy()


def verify_model_hashes():
    saved = json.loads((ARTIFACT_DIR / 'artifact_hashes.json').read_text())
    for filename in ('weighted_xgboost.ubj', 'preprocessor.joblib', 'metadata.json'):
        target = ARTIFACT_DIR / filename
        if sha256(target) != saved[filename]:
            raise RuntimeError(f'Model artifact hash mismatch: {filename}')
    print('[PASS] Detection checkpoint, preprocessor and metadata integrity', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--train-file', type=Path, default=DEFAULT_TRAIN,
                        help='Local canonical TRAIN CSV; defaults to backend/validation_data/...')
    parser.add_argument('--download', action='store_true', help='Download pinned TRAIN-only copy if absent')
    args = parser.parse_args()
    print('NETGUARD V1 -- SAVED WEIGHTED XGBOOST DEVELOPMENT VALIDATION REPLAY', flush=True)
    print('No training. No official TEST. No threshold tuning.', flush=True)
    if sklearn.__version__ != '1.6.1':
        raise RuntimeError(f'Use your .venv312 with scikit-learn 1.6.1, found {sklearn.__version__}')
    verify_model_hashes()
    train_file = args.train_file.resolve()
    ensure_verified_train(train_file, args.download)

    df = pd.read_csv(train_file, low_memory=False)
    if df.shape != (175341, 45):
        raise RuntimeError(f'UNSW TRAIN shape mismatch: {df.shape} != (175341,45)')
    counts = df['attack_cat'].astype(str).str.strip().value_counts().to_dict()
    if counts != EXPECTED_CLASS_COUNTS:
        raise RuntimeError('TRAIN class counts do not match notebook Cell 5')
    if not np.array_equal((df['attack_cat'].astype(str).str.strip() != 'Normal').astype(int).to_numpy(),
                          pd.to_numeric(df['label'], errors='coerce').to_numpy()):
        raise RuntimeError('Binary labels disagree with attack_cat')
    meta = json.loads((ARTIFACT_DIR / 'metadata.json').read_text())
    feat = meta['feature_columns']
    if len(feat) != 42 or any(f not in df.columns for f in feat):
        raise RuntimeError('Incorrect 42-column detector feature schema')
    Xv, yv = reconstruct_validation(df, feat)
    del df

    # Same formatting as the original notebook, Cell 7.
    for col in meta['categorical_columns']:
        Xv[col] = Xv[col].astype('string').fillna('__MISSING__').astype(str)
    for col in meta['numerical_columns']:
        Xv[col] = pd.to_numeric(Xv[col], errors='coerce').replace([np.inf, -np.inf], np.nan)

    print('Loading verified preprocessor and model...', flush=True)
    preprocessor = joblib.load(ARTIFACT_DIR / 'preprocessor.joblib')
    model = xgb.XGBClassifier()
    model.load_model(str(ARTIFACT_DIR / 'weighted_xgboost.ubj'))
    print('Transforming validation features...', flush=True)
    Xtrans = preprocessor.transform(Xv)
    if Xtrans.shape != (35167, 194):
        raise RuntimeError(f'Unexpected transformed matrix shape: {Xtrans.shape}')
    print('Predicting all 35,167 validation rows...', flush=True)
    proba = model.predict_proba(Xtrans)
    labels = meta['classes']
    if proba.shape != (35167, len(labels)) or not np.isfinite(proba).all():
        raise RuntimeError('Model probabilities invalid')
    if not np.allclose(proba.sum(axis=1), 1.0, atol=1e-5):
        raise RuntimeError('Class probabilities do not sum to 1')
    truth = pd.Categorical(yv, categories=labels).codes
    if np.any(truth < 0):
        raise RuntimeError('Unknown validation target')
    pred = proba.argmax(axis=1)
    metrics = {
        'Accuracy': float(accuracy_score(truth, pred)),
        'Macro F1': float(f1_score(truth, pred, average='macro', zero_division=0)),
        'Balanced accuracy': float(balanced_accuracy_score(truth, pred)),
        'Weighted F1': float(f1_score(truth, pred, average='weighted', zero_division=0)),
    }
    class_p, class_r, class_f1, class_n = precision_recall_fscore_support(
        truth, pred, labels=np.arange(len(labels)), zero_division=0
    )
    per_class = {name: {'support': int(class_n[i]), 'precision': float(class_p[i]),
                        'recall': float(class_r[i]), 'f1': float(class_f1[i])}
                 for i, name in enumerate(labels)}
    normal_idx = labels.index('Normal')
    binary_target = (truth != normal_idx).astype(int)
    attack_score = 1. - proba[:, normal_idx]
    binary = {
        'attack_average_precision': float(average_precision_score(binary_target, attack_score)),
        'attack_prevalence': float(binary_target.mean()),
        'threshold_0_5_precision': None,
        'threshold_0_5_recall': None,
    }
    from sklearn.metrics import precision_score, recall_score
    binary_pred = (attack_score >= 0.5).astype(int)
    binary['threshold_0_5_precision'] = float(precision_score(binary_target, binary_pred, zero_division=0))
    binary['threshold_0_5_recall'] = float(recall_score(binary_target, binary_pred, zero_division=0))

    expected = meta['validation_metrics']
    diffs = {key: abs(metrics[key] - float(expected[key])) for key in expected}
    match = all(d <= 0.00025 for d in diffs.values())
    report = {
        'evaluation_kind': 'SAVED_CHECKPOINT_DEV_VALIDATION_REPLAY_NOT_INDEPENDENT_TEST',
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'source_dataset': 'UNSW-NB15 canonical TRAIN only',
        'train_dataset_sha256': EXPECTED_TRAIN_SHA256,
        'development_train_rows': 140174,
        'development_validation_rows': 35167,
        'split': 'StratifiedGroupKFold(n_splits=5,shuffle=True,random_state=42), selected fold=4',
        'official_test_used': False,
        'weights_modified': False,
        'match_original_reported_metrics': match,
        'metrics': metrics,
        'original_notebook_metrics': expected,
        'absolute_metric_differences': diffs,
        'per_class': per_class,
        'derived_binary_attack': binary,
        'limitations': [
            'This is the development validation split reused during model selection, not independent testing.',
            'No threshold tuning or calibration was performed.',
            'No live traffic or external transfer evaluation was performed.',
        ],
        'environment': {
            'python': sys.version.split()[0], 'sklearn': sklearn.__version__,
            'xgboost': xgb.__version__, 'pandas': pd.__version__, 'numpy': np.__version__,
        },
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'match_original_reported_metrics': match, 'metrics': metrics,
                      'reported_metrics': expected, 'DoS_recall': per_class['DoS']['recall'],
                      'derived_binary_attack': binary}, indent=2), flush=True)
    print(f'[PASS] Saved report: {REPORT.relative_to(PROJECT)}', flush=True)
    if match:
        print('[PASS] Weighted XGBoost development-validation metrics reproduced', flush=True)
    else:
        print('[REVIEW] Replayed metrics differ from original notebook; do not freeze until investigated', flush=True)
        sys.exit(2)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'[FAILED] {type(e).__name__}: {e}', file=sys.stderr, flush=True)
        sys.exit(1)
