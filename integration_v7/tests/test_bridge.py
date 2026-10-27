import sys
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "rag"))
import rag_bridge
from app.schemas import AnalyzeRequest

FORECAST = {
    "id": 27, "event_type": "FORECAST_INFERENCE",
    "prediction": {
        "forecast": {"h5": .12, "h10": .32, "h15": .58},
        "family_eta": {"family_if_onset": "DOS_DDOS", "family_probability_if_onset": .753,
                       "conditional_eta_minutes": 14.2, "p_onset_within_15": .43},
    },
}
DETECT = {
    "id": 28, "event_type": "DETECTION_INFERENCE", "prediction": {
        "result": {"predicted_class": "DoS", "attack_probability": .88,
                   "probabilities": {"Normal": .12, "DoS": .74, "Exploits": .14}}
    },
}


def test_forwarded_forecast_is_saved_value_no_conditional_confusion():
    data = rag_bridge.build_analysis_request(FORECAST)
    clean = AnalyzeRequest.model_validate(data)
    assert clean.forecast_bundle.h10 == .32
    assert clean.family_eta.family_probability_if_onset == .753
    assert clean.family_eta.conditional_eta_minutes == 14.2
    assert clean.family_eta.p_onset_within_15 == .43
    assert clean.forecast is None
    assert clean.detection is None


def test_detection_class_confidence_is_own_class_score_not_any_attack():
    data = rag_bridge.build_analysis_request(DETECT)
    clean = AnalyzeRequest.model_validate(data)
    assert clean.detection.attack_class == "DoS"
    assert clean.detection.confidence == .74
    assert clean.family_eta is None


def test_rejects_unknown_future_family():
    bad = dict(FORECAST)
    bad["prediction"] = dict(FORECAST["prediction"])
    bad["prediction"]["family_eta"] = {**FORECAST["prediction"]["family_eta"], "family_if_onset": "DoS"}
    with pytest.raises(ValueError):
        rag_bridge.build_analysis_request(bad)


def test_endpoint_uses_backend_record_and_returns_rag_result(monkeypatch):
    monkeypatch.setattr(rag_bridge, "get_event", lambda record_id: FORECAST if record_id == 27 else None)
    observed = []
    monkeypatch.setattr(rag_bridge, "_rag_post", lambda payload: observed.append(payload) or {"summary": "Saved model forecast"})
    app = FastAPI()
    app.include_router(rag_bridge.router)
    client = TestClient(app)
    result = client.post("/api/rag/explain/history/27")
    assert result.status_code == 200
    assert result.json()["inference_id"] == 27
    assert observed[0]["forecast_bundle"]["h10"] == .32
    assert client.post("/api/rag/explain/history/404").status_code == 404
