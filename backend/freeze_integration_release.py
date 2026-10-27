"""Freeze verified NetGuard V1 artifacts for research-demo backend integration.

Read-only with respect to models, source datasets, and prior validation reports.
Writes only backend/model_release/netguard_v1_integration_freeze.json.
Does NOT train, evaluate TEST, calibrate, or claim production readiness.
Run from repository root: python backend/freeze_integration_release.py
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RELEASE = ROOT / "backend" / "model_release"
SOURCE = RELEASE / "netguard_v1_candidate.json"
FORECAST = RELEASE / "validation_windows_v1.json"
DETECTION = RELEASE / "detection_validation_v1.json"
DEST = RELEASE / "netguard_v1_integration_freeze.json"

EXPECTED_FORECAST_DATA_SHA = "45ed08b72400cd5d09a9ddbd082265a9e556fe5b38d925de08a23a313848008e"
EXPECTED_DETECTION_TRAIN_SHA = "bec7dd5ec88dc2a0ccc7a07879d338395ed7421750f675fd0339e07dfe0648fa"
EXPECTED_AP = {
    "stacked_lstm_v2": {"H5": .76100498, "H10": .90601750, "H15": .93585405},
    "competing_risk_lstm": {"H5": .72483581, "H10": .89913694, "H15": .93605927},
}
EXPECTED_DETECTION = {
    "Accuracy": .8167600307106094,
    "Macro F1": .6430739316136387,
    "Balanced accuracy": .655136402436738,
    "Weighted F1": .823378551145442,
}


def require(condition, msg):
    if not condition:
        raise RuntimeError(msg)


def read_json(path):
    require(path.is_file(), f"Missing required file: {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def approx(actual, expected, tolerance, label):
    require(isinstance(actual, (int, float)) and math.isfinite(actual), f"Invalid metric: {label}")
    require(abs(actual - expected) <= tolerance, f"Metric mismatch: {label}, got {actual}, expected {expected}")


def main():
    print("NetGuard V1 integration freeze: verifying evidence (no retraining, no TEST)", flush=True)
    cand = read_json(SOURCE)
    fc = read_json(FORECAST)
    det = read_json(DETECTION)

    require(cand.get("release_candidate") == "netguard-models-v1-candidate", "Unexpected source candidate")
    require(cand.get("status") == "ARTIFACT_INTEGRITY_AND_SYNTHETIC_INFERENCE_SMOKE_VERIFIED_ONLY", "Candidate status does not match verified smoke-test state")
    require(set(cand.get("models", {})) == {"weighted_xgboost_v2", "stacked_lstm_v2", "competing_risk_lstm"}, "Model selection changed")

    # Protect against accepting renamed/replaced weights by checking all candidate hashes again.
    for model_name, parts in cand["models"].items():
        for item_name, item in parts.items():
            p = (ROOT / item["path"]).resolve()
            require(p.is_relative_to(ROOT.resolve()), f"Artifact path escapes repository: {item['path']}")
            require(p.is_file(), f"Missing artifact {item['path']}")
            require(sha256(p) == item["sha256"], f"Artifact changed: {item['path']}")
        print(f"[PASS] {model_name} artifact hashes unchanged", flush=True)

    require(fc.get("evaluation_kind") == "FROZEN_SYNTHETIC_VALIDATION_REPLAY", "Wrong forecasting evaluation type")
    require(fc.get("dataset_sha256") == EXPECTED_FORECAST_DATA_SHA, "Forecast data checksum record mismatch")
    require(fc.get("sampling") == "full", "Forecasting evaluation must include all validation windows")
    require(fc.get("rows_evaluated") == 18839 and fc.get("unique_episodes_evaluated") == 300, "Incorrect forecasting validation coverage")
    for model_name, expected_horizons in EXPECTED_AP.items():
        actual = fc["model_metrics"][model_name]["horizons"]
        for horizon, ap in expected_horizons.items():
            approx(actual[horizon]["average_precision"], ap, .00005, f"{model_name}/{horizon}/AP")
    cr = fc["model_metrics"]["competing_risk_lstm"]["family_and_eta"]
    approx(cr["family_accuracy_given_true_onset"], .80888889, .00005, "CR family accuracy")
    approx(cr["family_macro_f1_given_true_onset"], .79582306, .00005, "CR family macro F1")
    approx(cr["conditional_eta_mae_minutes_given_true_onset"], 2.53653373, .00005, "CR ETA MAE")
    print("[PASS] Forecasting full synthetic validation reproduces saved research results", flush=True)

    require(det.get("evaluation_kind") == "SAVED_CHECKPOINT_DEV_VALIDATION_REPLAY_NOT_INDEPENDENT_TEST", "Wrong detection evaluation type")
    require(det.get("train_dataset_sha256") == EXPECTED_DETECTION_TRAIN_SHA, "Detector source TRAIN checksum mismatch")
    require(det.get("development_validation_rows") == 35167, "Incorrect detection validation coverage")
    require(det.get("match_original_reported_metrics") is True, "Detector did not reproduce original reported metrics")
    require(det.get("official_test_used") is False, "Detector report must not use official TEST")
    require(det.get("weights_modified") is False, "Detection report indicates modified weights")
    for k, expected in EXPECTED_DETECTION.items():
        approx(det["metrics"][k], expected, 1e-7, f"detector/{k}")
    approx(det["per_class"]["DoS"]["recall"], .6391065830721003, .00005, "detector/DoS recall")
    print("[PASS] Weighted XGBoost 35,167-row dev validation reproduces original metrics", flush=True)

    data_path = ROOT / "backend/validation_data/windows_W10_VALIDATION.npz"
    require(data_path.is_file(), "Frozen forecasting validation input is missing")
    require(sha256(data_path) == EXPECTED_FORECAST_DATA_SHA, "Frozen validation input altered")

    release = {
        "release_id": "netguard-models-v1.0.0-demo",
        "status": "FROZEN_FOR_RESEARCH_DEMO_INTEGRATION_DEV_VALIDATED",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Local/replay-backed FastAPI and React integration; not a real-world security deployment claim",
        "selection": {
            "current_attack_detection": "weighted_xgboost_v2",
            "multi_horizon_attack_forecast": "stacked_lstm_v2",
            "attack_family_and_conditional_eta": "competing_risk_lstm",
        },
        "models": cand["models"],
        "feature_contract": cand["feature_contract"],
        "environment_verified": cand["environment"],
        "evidence": {
            "candidate_manifest": {"path": str(SOURCE.relative_to(ROOT)), "sha256": sha256(SOURCE)},
            "forecast_validation": {"path": str(FORECAST.relative_to(ROOT)), "sha256": sha256(FORECAST),
                                     "evaluation_type": fc["evaluation_kind"], "rows": fc["rows_evaluated"],
                                     "unique_episodes": fc["unique_episodes_evaluated"],
                                     "metrics": fc["model_metrics"]},
            "detection_validation": {"path": str(DETECTION.relative_to(ROOT)), "sha256": sha256(DETECTION),
                                      "evaluation_type": det["evaluation_kind"],
                                      "rows": det["development_validation_rows"],
                                      "metrics": det["metrics"],
                                      "dos_recall": det["per_class"]["DoS"]["recall"]},
        },
        "restrictions": {
            "independent_test_confirmed": False,
            "live_network_forecasting_validated": False,
            "operational_probability_calibration_approved": False,
            "alert_thresholds_approved": False,
            "automatic_defense_approved": False,
            "synthetic_forecast_precursors": True,
        },
        "change_policy": "Any change to weights, scaler, preprocessor, feature order, or selection requires a new release id and revalidation",
    }
    DEST.parent.mkdir(exist_ok=True)
    if DEST.exists():
        previous = read_json(DEST)
        previous.pop("created_utc", None)
        proposed = dict(release)
        proposed.pop("created_utc", None)
        require(previous == proposed, "Existing frozen release differs. Refusing to overwrite it; version changes instead.")
        print(f"[PASS] Existing integration release unchanged: {DEST.relative_to(ROOT)}", flush=True)
        return
    DEST.write_text(json.dumps(release, indent=2) + "\n", encoding="utf-8")
    print(f"[PASS] Integration freeze created: {DEST.relative_to(ROOT)}", flush=True)
    print("[SCOPE] Research-demo integration ONLY. No independent TEST, calibration or live-traffic validation.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[FAILED] {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)
