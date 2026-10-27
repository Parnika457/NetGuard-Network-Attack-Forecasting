"""Read-only evaluation of frozen NetGuard forecasting models on VALIDATION windows.

This intentionally does not train, recalibrate, choose thresholds, or touch TEST.
Run from repository root with a Python 3.12 virtual environment:
  python backend/validate_forecast_windows.py --data backend/validation_data/windows_W10_VALIDATION.npz
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import sklearn
import torch
from sklearn.metrics import average_precision_score, roc_auc_score, brier_score_loss, f1_score

from netguard_models import (
    MODEL_FILES,
    CompetingRiskLSTM,
    StackedHorizonLSTM,
    process_history,
    read_json,
)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EXPECTED_VALIDATION_SHA256 = "45ed08b72400cd5d09a9ddbd082265a9e556fe5b38d925de08a23a313848008e"
HORIZONS = [5, 10, 15]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_checkpoint(which: str):
    paths = MODEL_FILES[which]
    record = read_json(paths["record"])
    scaler = read_json(paths["scaler"])
    if file_sha256(paths["model"]) != record["model_sha256"]:
        raise ValueError(f"Checkpoint SHA-256 mismatch for {which}")
    if file_sha256(paths["scaler"]) != record["scaler_sha256"]:
        raise ValueError(f"Scaler SHA-256 mismatch for {which}")
    if which == "stacked_lstm_v2":
        network = StackedHorizonLSTM(**record["model_architecture"])
    elif which == "competing_risk_lstm":
        network = CompetingRiskLSTM(**record["model_architecture"])
    else:
        raise ValueError(which)
    state_dict = torch.load(paths["model"], map_location="cpu", weights_only=True)
    network.load_state_dict(state_dict, strict=True)
    network.eval()
    return network, record, scaler


def scores_by_horizon(y: np.ndarray, scores: np.ndarray) -> dict:
    result = {}
    for j, horizon in enumerate(HORIZONS):
        yy = y[:, j].astype(int)
        pp = np.asarray(scores[:, j], dtype=np.float64)
        if not np.isfinite(pp).all() or not ((0 <= pp).all() and (pp <= 1).all()):
            raise ValueError("Invalid forecast probabilities")
        result[f"H{horizon}"] = {
            "average_precision": float(average_precision_score(yy, pp)),
            "roc_auc": float(roc_auc_score(yy, pp)) if np.unique(yy).size == 2 else None,
            "brier_score": float(brier_score_loss(yy, pp)),
            "prevalence": float(yy.mean()),
        }
    return result


def evaluate(data_path: Path, batch_size: int, limit: int) -> dict:
    if "TEST" in data_path.name.upper():
        raise ValueError("TEST split is intentionally not allowed by this validation script")
    if "VALIDATION" not in data_path.name.upper():
        raise ValueError("Use the frozen windows_W10_VALIDATION.npz file")
    observed = file_sha256(data_path)
    if observed != EXPECTED_VALIDATION_SHA256:
        raise ValueError(f"Validation file hash mismatch: {observed}. Do not use a modified file.")
    with np.load(data_path, allow_pickle=False) as archive:
        expected_keys = {"X", "y_horizons", "onset_class", "family_class", "episode_id", "minute"}
        if set(archive.files) != expected_keys:
            raise ValueError(f"Unexpected dataset keys: {archive.files}")
        total = int(archive["X"].shape[0])
        idx = np.arange(total)
        if limit:
            if limit < 10:
                raise ValueError("--limit must be 0 (all) or at least 10")
            # Deterministic representative subset spread throughout the file.
            idx = np.unique(np.linspace(0, total - 1, min(total, limit), dtype=int))
        X = archive["X"][idx]
        y = archive["y_horizons"][idx]
        onset_class = archive["onset_class"][idx]
        family_class = archive["family_class"][idx]
        episode_ids = archive["episode_id"][idx]
    if X.ndim != 3 or X.shape[1:] != (10, 14):
        raise ValueError(f"Invalid X shape: {X.shape}")
    if y.shape != (len(X), 3):
        raise ValueError(f"Invalid labels: {y.shape}")
    for j, horizon in enumerate(HORIZONS):
        if not np.array_equal(y[:, j].astype(bool), ((onset_class > 0) & (onset_class <= horizon))):
            raise ValueError(f"H{horizon} labels conflict with onset_class")
    if not np.array_equal(onset_class > 0, family_class > 0):
        raise ValueError("Family and onset labels disagree")
    if not np.isfinite(X).all() or (X < 0).any():
        raise ValueError("Input windows contain NaN/infinity or negative features")
    print(f"[PASS] Frozen VALIDATION checksum and labels; windows: {len(X):,} / {total:,}", flush=True)

    s_net, s_rec, s_scaler = load_checkpoint("stacked_lstm_v2")
    c_net, c_rec, c_scaler = load_checkpoint("competing_risk_lstm")
    if s_rec["feature_names"] != c_rec["feature_names"]:
        raise ValueError("Forecast models differ in feature order")
    print("[PASS] Both checkpoints loaded with strict=True", flush=True)
    s_outputs = []
    c_outputs = []
    torch.set_num_threads(1)
    with torch.inference_mode():
        for start in range(0, len(X), batch_size):
            chunk = X[start:start+batch_size]
            s_x = process_history(chunk, s_scaler, s_rec["feature_names"])
            c_x = process_history(chunk, c_scaler, c_rec["feature_names"])
            s_pred = s_net(torch.from_numpy(s_x)).numpy()
            c_joint = torch.softmax(c_net(torch.from_numpy(c_x)), dim=1).numpy()
            s_outputs.append(s_pred)
            c_outputs.append(c_joint)
            if (start//batch_size + 1) % 20 == 0:
                print(f"  Evaluated {min(start+batch_size, len(X)):,}/{len(X):,} windows", flush=True)
    stacked = np.concatenate(s_outputs).astype(np.float64)
    joint = np.concatenate(c_outputs).astype(np.float64)
    if stacked.shape != (len(X), 3) or joint.shape != (len(X), 76):
        raise ValueError("Bad model output dimensions")
    if not np.all((stacked[:, 0] <= stacked[:, 1]) & (stacked[:, 1] <= stacked[:, 2])):
        raise ValueError("Stacked outputs are not monotonic")
    if not np.allclose(joint.sum(axis=1), 1, atol=1e-5):
        raise ValueError("Competing-risk output distribution not normalized")
    family_minute = joint[:, 1:].reshape(-1, 15, 5)
    per_minute = family_minute.sum(axis=2)
    cr_horizons = np.cumsum(per_minute, axis=1)[:, [4, 9, 14]]
    positive = onset_class > 0
    family_prediction = 1 + np.argmax(family_minute.sum(axis=1), axis=1)
    p_event = per_minute.sum(axis=1)
    expected_eta = (per_minute * np.arange(1, 16)).sum(axis=1) / np.maximum(p_event, 1e-12)
    cr_detail = {
        "family_accuracy_given_true_onset": float((family_prediction[positive] == family_class[positive]).mean()),
        "family_macro_f1_given_true_onset": float(f1_score(family_class[positive], family_prediction[positive], labels=[1,2,3,4,5], average="macro", zero_division=0)),
        "conditional_eta_mae_minutes_given_true_onset": float(np.mean(np.abs(expected_eta[positive] - onset_class[positive]))),
        "note": "Metrics conditioned on actual onset use labels for evaluation only, not as prediction inputs.",
    }
    return {
        "evaluation_kind": "FROZEN_SYNTHETIC_VALIDATION_REPLAY",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_name": data_path.name,
        "dataset_sha256": observed,
        "rows_evaluated": len(X),
        "total_rows_available": total,
        "unique_episodes_evaluated": len(set(episode_ids.tolist())),
        "sampling": "full" if len(X) == total else "deterministic_subset_not_paper_comparable",
        "model_metrics": {
            "stacked_lstm_v2": {"horizons": scores_by_horizon(y, stacked)},
            "competing_risk_lstm": {"horizons": scores_by_horizon(y, cr_horizons), "family_and_eta": cr_detail},
        },
        "environment": {"python": platform.python_version(), "torch": torch.__version__, "scikit_learn": sklearn.__version__, "numpy": np.__version__},
        "limitations": [
            "Synthetic_NAF_v2 is simulated, not live recorded attack-precursor traffic",
            "This uses VALIDATION only and is not an independent real-world test",
            "No thresholds were selected or tuned",
            "The current detection XGBoost model is not evaluated by this forecasting-window file",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=HERE / "validation_data" / "windows_W10_VALIDATION.npz")
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--limit", type=int, default=0, help="For a quick subset check; 0 evaluates all validation windows")
    args = parser.parse_args()
    if args.batch_size <= 0:
        parser.error("--batch-size must be positive")
    print("NetGuard frozen VALIDATION replay (no training, no TEST)", flush=True)
    result = evaluate(args.data.resolve(), args.batch_size, args.limit)
    print(json.dumps(result, indent=2), flush=True)
    target = HERE / "model_release" / "validation_windows_v1.json"
    target.parent.mkdir(exist_ok=True, parents=True)
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"[PASS] Wrote report: {target.relative_to(ROOT)}", flush=True)


if __name__ == "__main__":
    main()
