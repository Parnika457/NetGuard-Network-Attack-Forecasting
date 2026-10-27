"""Inference-only loaders for the three NetGuard V1 selected checkpoints.

Architectures and preprocessing reconstructed from the committed training and
Network_Attack_Forecasting_Pipeline notebooks. No training, no scaler fitting.
Inputs to these functions must already match the training feature contract.
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
from torch import nn
import xgboost as xgb

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = PROJECT_ROOT / "model" / "artifacts"

DETECTION = ARTIFACT_ROOT / "current_detection" / "weighted_xgboost_v2"
STACKED = ARTIFACT_ROOT / "forecasting" / "stacked_lstm"
COMPETING = ARTIFACT_ROOT / "forecasting" / "competing_risk_lstm"

MODEL_FILES = {
    "weighted_xgboost_v2": {
        "model": DETECTION / "weighted_xgboost.ubj",
        "preprocessor": DETECTION / "preprocessor.joblib",
        "metadata": DETECTION / "metadata.json",
        "hashes": DETECTION / "artifact_hashes.json",
    },
    "stacked_lstm_v2": {
        "model": STACKED / "LSTM_V2_MONOTONIC_HORIZON_STATE.pt",
        "scaler": STACKED / "LSTM_V2_FULL_TRAIN_SCALER.json",
        "record": STACKED / "LSTM_V2_FINAL_TRAIN_RECORD.json",
    },
    "competing_risk_lstm": {
        "model": COMPETING / "LSTM_V2_CR_STATE.pt",
        "scaler": COMPETING / "LSTM_V2_CR_FULL_TRAIN_SCALER.json",
        "record": COMPETING / "LSTM_V2_CR_FINAL_TRAIN_RECORD.json",
    },
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class MonotonicHorizonHead(nn.Module):
    def __init__(self, input_dim: int):
        super().__init__()
        self.linear = nn.Linear(input_dim, 3)

    def forward(self, hidden: torch.Tensor) -> torch.Tensor:
        conditional = torch.sigmoid(self.linear(hidden))
        return 1.0 - torch.cumprod(1.0 - conditional, dim=-1)


class StackedHorizonLSTM(nn.Module):
    """Exact inference graph of the frozen monotonic LSTM from the pipeline notebook."""
    def __init__(self, input_dim: int, hidden_dim: int, dense_dim: int, num_layers: int, dropout: float = 0.0):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers=num_layers, batch_first=True)
        self.projection = nn.Sequential(nn.Linear(hidden_dim, dense_dim), nn.ReLU(), nn.Dropout(dropout))
        self.head = MonotonicHorizonHead(dense_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        sequence, _ = self.lstm(x)
        return self.head(self.projection(sequence[:, -1, :]))


class CompetingRiskLSTM(nn.Module):
    """Exact 76-class inference graph from Network_Attack_Forecasting_Pipeline."""
    def __init__(self, input_dim: int, hidden_dim: int, dense_dim: int,
                 num_layers: int, num_classes: int, dropout: float):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers=num_layers,
                            batch_first=True, dropout=dropout if num_layers > 1 else 0.0)
        self.projection = nn.Sequential(nn.Linear(hidden_dim, dense_dim), nn.ReLU(), nn.Dropout(dropout))
        self.classifier = nn.Linear(dense_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        sequence, _ = self.lstm(x)
        return self.classifier(self.projection(sequence[:, -1, :]))


def process_history(window, scaler: dict, feature_order: list[str]) -> np.ndarray:
    """One or multiple windows: raw nonnegative features, ordered oldest->newest."""
    x = np.asarray(window, dtype=np.float32)
    if x.shape == (10, 14):
        x = x[None, ...]
    if x.ndim != 3 or x.shape[1:] != (10, 14):
        raise ValueError(f"Expected (10,14) or (N,10,14); got {x.shape}")
    if not np.isfinite(x).all() or (x < 0).any():
        raise ValueError("Forecasting window must contain finite, nonnegative raw features")
    if list(scaler['feature_names']) != list(feature_order):
        raise ValueError("Scaler feature names/order differ from training record")
    median = np.asarray(scaler['median'], dtype=np.float32)
    scale = np.asarray(scaler['scale'], dtype=np.float32)
    clip_value = float(scaler['clip_value'])
    if median.shape != (14,) or scale.shape != (14,) or not np.isfinite(median).all() or not np.isfinite(scale).all() or (scale <= 0).any() or clip_value <= 0:
        raise ValueError("Invalid saved scaler parameters")
    x = (np.log1p(x) - median[None, None, :]) / scale[None, None, :]
    return np.ascontiguousarray(np.clip(x, -clip_value, clip_value), dtype=np.float32)


class NetGuardModels:
    def __init__(self):
        self.device = torch.device("cpu")  # Stable local Mac/Windows/Colab inference
        self.detection_meta = read_json(MODEL_FILES['weighted_xgboost_v2']['metadata'])
        self.stacked_record = read_json(MODEL_FILES['stacked_lstm_v2']['record'])
        self.cr_record = read_json(MODEL_FILES['competing_risk_lstm']['record'])
        self.stacked_scaler = read_json(MODEL_FILES['stacked_lstm_v2']['scaler'])
        self.cr_scaler = read_json(MODEL_FILES['competing_risk_lstm']['scaler'])

        self.detector = xgb.XGBClassifier()
        self.detector.load_model(str(MODEL_FILES['weighted_xgboost_v2']['model']))
        # Joblib uses pickle internally: only load this known, hash-checked project artifact.
        self.preprocessor = joblib.load(MODEL_FILES['weighted_xgboost_v2']['preprocessor'])
        if len(self.detector.classes_) != len(self.detection_meta['classes']):
            raise ValueError("Detection class count mismatch")

        self.stacked = StackedHorizonLSTM(**self.stacked_record['model_architecture'])
        self.stacked.load_state_dict(torch.load(MODEL_FILES['stacked_lstm_v2']['model'], map_location="cpu", weights_only=True), strict=True)
        self.stacked.eval()

        self.cr = CompetingRiskLSTM(**self.cr_record['model_architecture'])
        self.cr.load_state_dict(torch.load(MODEL_FILES['competing_risk_lstm']['model'], map_location="cpu", weights_only=True), strict=True)
        self.cr.eval()

    def forecast(self, window) -> dict:
        """Two independent model outputs; DON'T assume they are mutually calibrated."""
        s = process_history(window, self.stacked_scaler, self.stacked_record['feature_names'])
        c = process_history(window, self.cr_scaler, self.cr_record['feature_names'])
        if s.shape[0] != 1:
            raise ValueError("This demo forecast endpoint accepts one 10x14 window")
        with torch.inference_mode():
            p = self.stacked(torch.from_numpy(s)).numpy()[0].astype(float)
            cr_joint = torch.softmax(self.cr(torch.from_numpy(c)), dim=-1).numpy()[0].astype(float)
        if not (np.isfinite(p).all() and 0 <= p[0] <= p[1] <= p[2] <= 1):
            raise RuntimeError("Stacked LSTM probability invariants failed")
        if cr_joint.shape != (76,) or not np.isclose(cr_joint.sum(), 1., atol=1e-5):
            raise RuntimeError("Competing risk distribution invariants failed")
        family_names = self.cr_record['output_definition']['family_names']
        tm = cr_joint[1:].reshape(15, 5)
        family_mass = tm.sum(axis=0)
        minute_mass = tm.sum(axis=1)
        event_p = float(minute_mass.sum())
        conditional_family = (family_mass / event_p) if event_p > 1e-12 else None
        conditional_eta = float(np.dot(np.arange(1, 16), minute_mass / event_p)) if event_p > 1e-12 else None
        best_family = int(np.argmax(conditional_family)) if conditional_family is not None else None
        return {
            'stacked_lstm_v2': {'h5': float(p[0]), 'h10': float(p[1]), 'h15': float(p[2])},
            'competing_risk_lstm': {
                'p_no_onset_within_15': float(cr_joint[0]),
                'p_onset_within_15': event_p,
                'h5': float(minute_mass[:5].sum()),
                'h10': float(minute_mass[:10].sum()),
                'h15': event_p,
                'family_if_onset': family_names[best_family] if best_family is not None else None,
                'family_probability_if_onset': float(conditional_family[best_family]) if best_family is not None else None,
                'conditional_eta_minutes': conditional_eta,
                'minute_probabilities': minute_mass.tolist(),
            },
        }

    def detect(self, records: dict | list[dict], threshold: float = 0.5) -> list[dict]:
        """Current detection expects 42 UNSW-NB15 derived flow features."""
        if not 0 <= threshold <= 1:
            raise ValueError("threshold must be in [0,1]")
        if isinstance(records, dict):
            records = [records]
        frame = pd.DataFrame(records)
        features = self.detection_meta['feature_columns']
        missing = [name for name in features if name not in frame.columns]
        if missing:
            raise ValueError(f"Missing detector inputs: {missing}")
        frame = frame[features].copy()
        for col in self.detection_meta['categorical_columns']:
            frame[col] = frame[col].astype('string').fillna('__MISSING__').astype(str)
        for col in self.detection_meta['numerical_columns']:
            frame[col] = pd.to_numeric(frame[col], errors='coerce').replace([np.inf, -np.inf], np.nan)
        data = self.preprocessor.transform(frame)
        probabilities = self.detector.predict_proba(data)
        classes = self.detection_meta['classes']
        normal_i = classes.index('Normal')
        out = []
        for row in probabilities:
            attack_probability = float(1.0 - row[normal_i])
            non_normal = [i for i, name in enumerate(classes) if name != 'Normal']
            attack_i = max(non_normal, key=lambda i: row[i])
            detected = attack_probability >= threshold
            out.append({
                'current_attack_detected': detected,
                'attack_probability': attack_probability,
                'predicted_class': classes[attack_i] if detected else 'Normal',
                'probabilities': {label: float(row[i]) for i, label in enumerate(classes)},
                'threshold': threshold,
            })
        return out
