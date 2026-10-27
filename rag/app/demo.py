"""End-to-end demo after ingestion + RAG service dependencies + API key are configured."""
import json
import requests

SAMPLE = {
    "question": "Explain the detected DoS class and the general 10-minute attack forecast. What should be checked next?",
    "detection": {"attack_class": "DoS", "confidence": 0.91, "model_name": "DEMO_NOT_LIVE"},
    "forecast": {"horizon_minutes": 10, "probability": 0.73, "target": "any_attack", "model_name": "DEMO_NOT_LIVE"},
    "observations": {"protocol": "TCP", "flow_count": 900, "window_minutes": 10},
    "top_k": 6,
}


def main():
    print("DEMO INPUT ONLY — these predictions are invented to test RAG wiring, not real model inference.")
    response = requests.post("http://127.0.0.1:8001/api/rag/analyze", json=SAMPLE, timeout=120)
    response.raise_for_status()
    print(json.dumps(response.json(), indent=2))


if __name__ == "__main__":
    main()
