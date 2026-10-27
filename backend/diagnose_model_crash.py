"""NetGuard crash diagnostic. Read-only: does not train, change, or overwrite weights.

Place this file inside the project's backend/ folder and run from the project root:
    python backend/diagnose_model_crash.py

Runs the XGBoost, stacked-LSTM, and competing-risk model checks in separate
Python child processes, then runs the combined loader if all three pass.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
if not (HERE / "netguard_models.py").is_file():
    raise SystemExit("Place diagnose_model_crash.py alongside backend/netguard_models.py")

ENV = os.environ.copy()
for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    ENV[key] = "1"
ENV["PYTHONUNBUFFERED"] = "1"

TESTS = {
    "detection": '''
import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from netguard_models import MODEL_FILES, read_json
files = MODEL_FILES["weighted_xgboost_v2"]
print("D1: constructing XGBoost classifier", flush=True)
model = xgb.XGBClassifier()
print("D2: loading weighted model file", flush=True)
model.load_model(str(files["model"]))
print("D3: loading saved preprocessor", flush=True)
preprocessor = joblib.load(files["preprocessor"])
print("D4: preparing one artificial test row", flush=True)
meta = read_json(files["metadata"])
row = {name: 0 for name in meta["feature_columns"]}
row.update({"proto": "tcp", "service": "-", "state": "FIN"})
frame = pd.DataFrame([row])[meta["feature_columns"]].copy()
for name in meta["categorical_columns"]:
    frame[name] = frame[name].astype("string").fillna("__MISSING__").astype(str)
for name in meta["numerical_columns"]:
    frame[name] = pd.to_numeric(frame[name], errors="coerce").replace([np.inf, -np.inf], np.nan)
print("D5: transforming 42 detector input features", flush=True)
features = preprocessor.transform(frame)
print("D6: running classifier.predict_proba (transformed shape", features.shape, ")", flush=True)
proba = model.predict_proba(features)
assert proba.shape == (1, 10), proba.shape
print("DETECTION PASS", flush=True)
''',
    "stacked_lstm": '''
import numpy as np
import torch
from netguard_models import MODEL_FILES, read_json, StackedHorizonLSTM, process_history
files = MODEL_FILES["stacked_lstm_v2"]
print("S1: reading architecture and scaler", flush=True)
record = read_json(files["record"]); scaler = read_json(files["scaler"])
print("S2: constructing stacked LSTM", flush=True)
model = StackedHorizonLSTM(**record["model_architecture"])
print("S3: torch.load state dictionary", flush=True)
weights = torch.load(files["model"], map_location="cpu", weights_only=True)
print("S4: load_state_dict(strict=True)", flush=True)
model.load_state_dict(weights, strict=True); model.eval()
print("S5: preprocess synthetic 10x14 window", flush=True)
x = process_history(np.zeros((10,14), dtype=np.float32), scaler, record["feature_names"])
print("S6: stacked LSTM forward pass", flush=True)
with torch.inference_mode():
    pred = model(torch.from_numpy(x)).numpy()
assert pred.shape == (1,3), pred.shape
print("STACKED LSTM PASS", flush=True)
''',
    "competing_risk_lstm": '''
import numpy as np
import torch
from netguard_models import MODEL_FILES, read_json, CompetingRiskLSTM, process_history
files = MODEL_FILES["competing_risk_lstm"]
print("C1: reading architecture and scaler", flush=True)
record = read_json(files["record"]); scaler = read_json(files["scaler"])
print("C2: constructing competing-risk LSTM", flush=True)
model = CompetingRiskLSTM(**record["model_architecture"])
print("C3: torch.load state dictionary", flush=True)
weights = torch.load(files["model"], map_location="cpu", weights_only=True)
print("C4: load_state_dict(strict=True)", flush=True)
model.load_state_dict(weights, strict=True); model.eval()
print("C5: preprocess synthetic 10x14 window", flush=True)
x = process_history(np.zeros((10,14), dtype=np.float32), scaler, record["feature_names"])
print("C6: competing-risk forward pass", flush=True)
with torch.inference_mode():
    pred = model(torch.from_numpy(x))
    proba = torch.softmax(pred, dim=-1).numpy()
assert proba.shape == (1,76), proba.shape
print("COMPETING-RISK LSTM PASS", flush=True)
''',
    "combined": '''
import numpy as np
from netguard_models import NetGuardModels
print("ALL1: constructing NetGuardModels (all models in one process)", flush=True)
models = NetGuardModels()
print("ALL2: forecasting", flush=True)
result = models.forecast(np.zeros((10,14), dtype=np.float32))
print("ALL3: detection", flush=True)
meta = models.detection_meta
row = {name: 0 for name in meta["feature_columns"]}
row.update({"proto": "tcp", "service": "-", "state": "FIN"})
models.detect(row)
print("COMBINED PASS", flush=True)
''',
}


def run_stage(stage: str, source: str) -> bool:
    print(f"\n{'='*13} {stage.upper()} {'='*13}", flush=True)
    proc = subprocess.run(
        [sys.executable, "-X", "faulthandler", "-u", "-c", source],
        cwd=HERE, env=ENV, check=False,
    )
    if proc.returncode == 0:
        print(f"[PASS] {stage}", flush=True)
        return True
    if proc.returncode < 0:
        print(f"[CRASH] {stage}: terminated by signal {-proc.returncode}", flush=True)
    else:
        print(f"[FAILED] {stage}: process exit code {proc.returncode}", flush=True)
    return False


def main() -> int:
    print("NetGuard model crash diagnostic (READ ONLY)", flush=True)
    print(f"Python: {sys.version.split()[0]} | Interpreter: {sys.executable}", flush=True)
    print(f"Project: {PROJECT_ROOT}", flush=True)
    results = {name: run_stage(name, TESTS[name]) for name in ("detection", "stacked_lstm", "competing_risk_lstm")}
    if all(results.values()):
        results["combined"] = run_stage("combined", TESTS["combined"])
    else:
        print("\n[SKIP] combined test until individual failures are diagnosed", flush=True)
    print("\nSUMMARY: " + ", ".join(f"{name}={'PASS' if passed else 'FAIL/CRASH'}" for name, passed in results.items()), flush=True)
    print("No model weights, code, or release manifests were changed.", flush=True)
    return 0 if all(results.values()) else 1

if __name__ == "__main__":
    raise SystemExit(main())
