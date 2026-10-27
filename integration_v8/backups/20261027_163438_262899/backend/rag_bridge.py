"""RAG explanations of SAVED NetGuard predictions. Never recompute ML or trust browser-supplied scores."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from fastapi import APIRouter, HTTPException
from event_store import get_event

router = APIRouter()
RAG_URL = os.environ.get("NETGUARD_RAG_URL", "http://127.0.0.1:8001").rstrip("/")
_FAMILIES = {"BRUTE_AUTH", "DOS_DDOS", "EXPLOIT_APP", "FUZZING", "RECON_SCAN"}
_DETECTION_CLASSES = {"Normal", "Analysis", "Backdoor", "DoS", "Exploits", "Fuzzers", "Generic", "Reconnaissance", "Shellcode", "Worms"}


def build_analysis_request(record: dict[str, Any]) -> dict[str, Any]:
    """Exact inference contract; no estimated or guessed model scores."""
    prediction = record.get("prediction") or {}
    event_type = record.get("event_type")
    if event_type == "FORECAST_INFERENCE":
        horizons = prediction.get("forecast") or {}
        eta = prediction.get("family_eta") or {}
        bundle = {
            "h5": horizons["h5"], "h10": horizons["h10"], "h15": horizons["h15"],
            "model_name": "stacked_lstm_v2",
        }
        family = eta.get("family_if_onset")
        if family is not None and family not in _FAMILIES:
            raise ValueError("Unknown competing-risk future family")
        conditional = {
            "family_if_onset": family,
            "family_probability_if_onset": eta.get("family_probability_if_onset"),
            "conditional_eta_minutes": eta.get("conditional_eta_minutes"),
            "p_onset_within_15": eta["p_onset_within_15"],
            "conditioning_horizon_minutes": 15,
            "model_name": "competing_risk_lstm",
        }
        return {
            "question": "Explain these attack-onset forecasts and their conditional future-family/ETA estimates. Give concise evidence-grounded defensive investigation steps for this simulated prediction.",
            "forecast_bundle": bundle,
            "family_eta": conditional,
            "top_k": 5,
        }
    if event_type == "DETECTION_INFERENCE":
        result = prediction.get("result") or {}
        label = result["predicted_class"]
        if label not in _DETECTION_CLASSES:
            raise ValueError("Unknown current-detection class")
        confidence = result["probabilities"][label]
        return {
            "question": "Explain the saved present-traffic classification without treating it as a confirmed incident; suggest practical verification and defensive investigation steps.",
            "detection": {
                "attack_class": label, "confidence": confidence,
                "model_name": "weighted_xgboost_v2",
            },
            "top_k": 5,
        }
    raise ValueError("This record is not a model inference")


def _rag_post(payload: dict) -> dict:
    req = urllib.request.Request(
        f"{RAG_URL}/api/rag/analyze",
        data=json.dumps(payload, allow_nan=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            data = json.load(response)
            if not isinstance(data, dict) or not isinstance(data.get("summary"), str):
                raise ValueError("Unexpected RAG response")
            return data
    except urllib.error.HTTPError as exc:
        # Do not pass through Gemini error strings or sensitive provider metadata.
        if exc.code in (400, 422):
            raise HTTPException(502, "RAG request contract mismatch. Verify the V7 RAG update is installed.") from exc
        raise HTTPException(503, "RAG analysis unavailable. Check that RAG is running and Gemini is accessible.") from exc
    except (TimeoutError, urllib.error.URLError) as exc:
        raise HTTPException(503, "RAG service unavailable. Start the RAG server on port 8001.") from exc
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(502, "RAG returned an unexpected response.") from exc


@router.post("/api/rag/explain/history/{event_id}")
def explain_saved_inference(event_id: int):
    record = get_event(event_id)
    if record is None:
        raise HTTPException(404, "Saved inference not found")
    try:
        payload = build_analysis_request(record)
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(422, "This saved inference has incomplete or incompatible model data") from exc
    result = _rag_post(payload)
    return {"inference_id": event_id, "analysis": result}
