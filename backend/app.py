"""NetGuard V1 research-demo integration API.

Runs frozen local checkpoints. Replay input is simulated Synthetic_NAF_v2
validation windows, not live traffic. Never reads TEST partition.
"""
from __future__ import annotations

import hashlib
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import numpy as np
import sklearn
import torch
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from netguard_models import NetGuardModels, process_history
from event_store import init_database, save_forecast_event, save_detection_event, list_events, get_event
from replay_telemetry import extract_telemetry, build_risk_history
from live_telemetry import available_interfaces, read_interface  # LIVE HOST TELEMETRY MODE (V3)

ROOT = Path(__file__).resolve().parents[1]
RELEASE_FILE = ROOT / "backend/model_release/netguard_v1_integration_freeze.json"
REPLAY_FILE = ROOT / "backend/validation_data/windows_W10_VALIDATION.npz"
REPLAY_SHA = "45ed08b72400cd5d09a9ddbd082265a9e556fe5b38d925de08a23a313848008e"
RELEASE_ID = "netguard-models-v1.0.0-demo"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for piece in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(piece)
    return digest.hexdigest()


def _check_frozen_release() -> dict:
    if not RELEASE_FILE.is_file():
        raise RuntimeError("Integration freeze missing. Run python backend/freeze_integration_release.py")
    release = json.loads(RELEASE_FILE.read_text(encoding="utf-8"))
    if release.get("release_id") != RELEASE_ID or release.get("status") != "FROZEN_FOR_RESEARCH_DEMO_INTEGRATION_DEV_VALIDATED":
        raise RuntimeError("Unexpected or unverified model release")
    if sklearn.__version__ != "1.6.1":
        raise RuntimeError("Frozen detector requires scikit-learn==1.6.1")
    expected_models = {"weighted_xgboost_v2", "stacked_lstm_v2", "competing_risk_lstm"}
    if set(release.get("models", {})) != expected_models:
        raise RuntimeError("Unexpected model selection in frozen release")
    for model, parts in release["models"].items():
        for name, metadata in parts.items():
            path = (ROOT / metadata["path"]).resolve()
            if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
                raise RuntimeError(f"Missing/unsafe model artifact: {model}/{name}")
            if _sha256(path) != metadata["sha256"]:
                raise RuntimeError(f"Frozen artifact changed: {model}/{name}")
    return release


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Apply single-thread settings via run_api.py BEFORE importing NumPy/PyTorch.
    release = _check_frozen_release()
    torch.set_num_threads(1)
    app.state.models = NetGuardModels()
    app.state.release = release
    init_database()
    # Hash check BEFORE loading. Do not read dataset labels as model inputs.
    if not REPLAY_FILE.is_file():
        app.state.replay = None
        print("[WARN] Replay validation file missing; /api/forecast and /api/detect remain usable")
    else:
        if _sha256(REPLAY_FILE) != REPLAY_SHA:
            raise RuntimeError("Validation replay data hash mismatch")
        with np.load(REPLAY_FILE, allow_pickle=False) as file:
            app.state.replay = {
                "X": file["X"].copy(),
                "minute": file["minute"].copy(),
                "episode_id": file["episode_id"].copy(),
            }
        if app.state.replay["X"].shape != (18839, 10, 14):
            raise RuntimeError("Unexpected frozen validation window shape")
    yield
    app.state.models = None
    app.state.replay = None


api = FastAPI(
    title="NetGuard Research Demo API",
    description="Frozen checkpoints; simulated forecasting replay; no live monitoring or automatic defense.",
    version="1.0.0-demo",
    lifespan=lifespan,
)


class ForecastRequest(BaseModel):
    window: list[list[float]] = Field(description="10 oldest-to-newest rows of 14 raw nonnegative features")


class DetectionRequest(BaseModel):
    features: dict[str, Any] = Field(description="All 42 UNSW-NB15 flow features")
    threshold: float = Field(default=0.5, ge=0.0, le=1.0)


def _forecast(window):
    try:
        result = api.state.models.forecast(window)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "forecast": result["stacked_lstm_v2"],
        "family_eta": result["competing_risk_lstm"],
        "models": {"risk": "stacked_lstm_v2", "family_eta": "competing_risk_lstm"},
        "model_release": RELEASE_ID,
        "disclaimer": "Development-validated on simulated precursor data; not calibrated for operational alerts.",
    }


@api.get("/api/health")
def health():
    return {
        "status": "ok", "models_loaded": api.state.models is not None,
        "release": RELEASE_ID, "mode": "research_demo",
        "forecast_replay_available": api.state.replay is not None,
        "live_network_monitoring": False,
    }


@api.post("/api/forecast")
def predict_forecast(request: ForecastRequest):
    if len(request.window) != 10 or any(len(row) != 14 for row in request.window):
        raise HTTPException(status_code=422, detail="Expected 10 rows of 14 raw forecasting features")
    result = _forecast(request.window)
    return {"mode": "provided_window", **result}


@api.post("/api/detect")
def predict_detection(request: DetectionRequest):
    try:
        result = api.state.models.detect(request.features, threshold=request.threshold)[0]
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    payload = {
        "mode": "provided_flow", "model": "weighted_xgboost_v2",
        "model_release": RELEASE_ID, "result": result,
        "disclaimer": "Detection threshold is exploratory, not operationally calibrated.",
    }
    saved = save_detection_event(payload)
    return {**payload, "history": {"id": saved["id"], "recorded_utc": saved["created_utc"]}}


@api.get("/api/replay/forecast")
def replay_forecast(index: int = Query(default=0, ge=0, le=18838)):
    dataset = api.state.replay
    if dataset is None:
        raise HTTPException(status_code=503, detail="Frozen validation replay file not available")
    if index >= len(dataset["X"]):
        raise HTTPException(status_code=404, detail="Replay window index out of bounds")
    return _build_replay(index)


# Read-only replay and explicit recording are intentionally separate.
# Viewing API documentation or previewing a window does not create a history event.

def _build_replay(index: int) -> dict:
    data = api.state.replay
    if data is None:
        raise HTTPException(status_code=503, detail="Frozen validation replay file not available")
    if not 0 <= index < len(data["X"]):
        raise HTTPException(status_code=404, detail="Replay index out of bounds")
    window = data["X"][index]  # 10x14 raw features; NO future labels
    inference = _forecast(window)
    models = api.state.models
    episode_id = str(data["episode_id"][index])
    timeline_start = max(0, index - 8)
    indices = [i for i in range(timeline_start, index + 1)
               if str(data["episode_id"][i]) == episode_id]
    recent = data["X"][indices]
    processed = process_history(recent, models.stacked_scaler,
                                models.stacked_record["feature_names"])
    with torch.inference_mode():
        horizon_probs = models.stacked(torch.from_numpy(processed)).numpy()
    risk_history = build_risk_history(indices, data["minute"], horizon_probs)
    return {
        "mode": "synthetic_validation_replay", "dataset": "Synthetic_NAF_v2",
        "index": index, "total_windows": len(data["X"]),
        "episode_id": episode_id, "episode_minute": int(data["minute"][index]),
        "telemetry": extract_telemetry(window, int(data["minute"][index]), risk_history),
        **inference,
    }


@api.post("/api/replay/step")
def step_replay(index: int = Query(default=0, ge=0, le=18838)):
    """Explicit user-requested inference replay; records exactly one row per replay index."""
    payload = _build_replay(index)
    saved = save_forecast_event(payload)
    return {**payload, "history": {"id": saved["id"], "recorded_utc": saved["created_utc"]}}


@api.get("/api/history")
def history(limit: int = Query(default=50, ge=1, le=100),
            offset: int = Query(default=0, ge=0)):
    return list_events(limit, offset)


@api.get("/api/history/{event_id}")
def history_event(event_id: int):
    event = get_event(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="History event not found")
    return event


@api.get("/api/live/interfaces")
def live_interfaces():
    """List active host interfaces; no packet capture or model inference."""
    return available_interfaces()


@api.get("/api/live/metrics")
def live_metrics(interface: str | None = Query(default=None)):
    """Read the OS network interface counters from the API host."""
    try:
        return read_interface(interface)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

# NETGUARD_RAG_V7_ROUTE
from rag_bridge import router as rag_router
api.include_router(rag_router)
