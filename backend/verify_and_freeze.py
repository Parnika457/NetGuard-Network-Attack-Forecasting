"""Check source artifact hashes and model inference, then write a CANDIDATE lockfile.

Run: python backend/verify_and_freeze.py
This is *not* an independent accuracy or calibration validation.
"""
from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import sklearn
import torch
import xgboost

from netguard_models import MODEL_FILES, NetGuardModels, read_json

HERE = Path(__file__).resolve().parent
RELEASE_FILE = HERE / 'model_release' / 'netguard_v1_candidate.json'


def sha256(path: Path) -> str:
    d = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            d.update(block)
    return d.hexdigest()


def verified_artifacts():
    output = {}
    for model_name, parts in MODEL_FILES.items():
        if model_name == 'weighted_xgboost_v2':
            saved_hashes = read_json(parts['hashes'])
            for label in ['model', 'preprocessor', 'metadata']:
                target = parts[label]
                observed = sha256(target)
                expected = saved_hashes[target.name]
                if observed != expected:
                    raise RuntimeError(f'HASH MISMATCH: {target}')
        else:
            record = read_json(parts['record'])
            for label in ['model', 'scaler']:
                target = parts[label]
                observed = sha256(target)
                expected = record['model_sha256' if label == 'model' else 'scaler_sha256']
                if observed != expected:
                    raise RuntimeError(f'HASH MISMATCH: {target}')
        output[model_name] = {
            label: {'path': str(path.relative_to(HERE.parent)), 'sha256': sha256(path)}
            for label, path in parts.items() if label != 'hashes'
        }
        print(f'[PASS] {model_name}: original files match saved hashes')
    return output


def smoke_test():
    models = NetGuardModels()
    # Synthetic zeros test shape/math ONLY. This is NOT a realistic network sample.
    sample_window = np.zeros((10, 14), dtype=np.float32)
    forecast = models.forecast(sample_window)
    print('[PASS] Stacked-LSTM: 3 cumulative horizon outputs')
    print('[PASS] Competing-risk LSTM: 76-class distribution and onset decoder')

    d = models.detection_meta
    artificial_row = {feature: 0 for feature in d['feature_columns']}
    artificial_row.update({'proto': 'tcp', 'service': '-', 'state': 'FIN'})
    detected = models.detect(artificial_row)
    assert len(detected) == 1 and len(detected[0]['probabilities']) == 10
    print('[PASS] Weighted-XGBoost V2: preprocessor + 10-class inference')
    print('[NOTE] Output values below are from ARTIFICIAL TEST INPUTS, not real traffic')
    print(json.dumps({'forecast': forecast, 'current_detection': detected[0]}, indent=2))
    return True


def main():
    print('NETGUARD V1 -- ARTIFACT INTEGRITY + INFERENCE SMOKE TEST')
    artifacts = verified_artifacts()  # Check before joblib.load (pickle).
    if sklearn.__version__ != '1.6.1':
        raise RuntimeError(
            f'The detector preprocessor requires scikit-learn==1.6.1, '
            f'but this environment has {sklearn.__version__}. '
            'Create a fresh .venv and install backend/requirements.txt.'
        )
    smoke_test()
    record = {
        'release_candidate': 'netguard-models-v1-candidate',
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'status': 'ARTIFACT_INTEGRITY_AND_SYNTHETIC_INFERENCE_SMOKE_VERIFIED_ONLY',
        'not_yet_verified': [
            'matching original saved validation predictions on real windows',
            'independent test-set performance',
            'probability calibration and alert thresholds',
            'live network input integration',
        ],
        'models': artifacts,
        'feature_contract': {
            'forecast': {'shape': [10, 14], 'time_order': 'oldest_to_newest',
                         'feature_order': read_json(MODEL_FILES['stacked_lstm_v2']['record'])['feature_names'],
                         'preprocessing': 'log1p -> saved median/IQR -> clip[-8,8]'},
            'current_detection': {'feature_order': read_json(MODEL_FILES['weighted_xgboost_v2']['metadata'])['feature_columns'],
                                  'preprocessing': 'saved joblib pipeline'},
        },
        'environment': {
            'python': platform.python_version(), 'torch': torch.__version__,
            'xgboost': xgboost.__version__, 'scikit_learn': sklearn.__version__,
            'numpy': np.__version__, 'joblib': joblib.__version__,
        },
    }
    RELEASE_FILE.parent.mkdir(parents=True, exist_ok=True)
    RELEASE_FILE.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(f'\nCANDIDATE lockfile created: {RELEASE_FILE.relative_to(HERE.parent)}')
    print('No weights changed. No model trained. This is not the final production freeze.')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'\n[FAILED] {type(e).__name__}: {e}', file=sys.stderr)
        sys.exit(1)
