"""Observed numeric features in frozen simulated 10x14 windows; no fake protocols."""
from __future__ import annotations
import numpy as np

# Frozen feature order is in backend/model_release/netguard_v1_integration_freeze.json.
FLOW_COUNT, FLOW_DUR_MEAN, FLOW_DUR_STD, FLOW_DUR_MAX = range(4)
FWD_PKTS, BWD_PKTS, TOTAL_PKTS, FWD_BYTES, BWD_BYTES, TOTAL_BYTES, PPS, BPS = range(4,12)
MIB = 1024.0 ** 2
KIB = 1024.0


def extract_telemetry(window, end_minute: int, risk_history: list[dict]) -> dict:
    data = np.asarray(window, dtype=np.float64)
    if data.shape != (10,14) or not np.isfinite(data).all():
        raise ValueError("Invalid replay telemetry window")
    latest = data[-1]
    fwd, bwd = float(latest[FWD_PKTS]), float(latest[BWD_PKTS])
    total = fwd + bwd
    breakdown = [
        {"name": "Forward packets", "value": 100.0 * fwd / total if total else 0.0},
        {"name": "Backward packets", "value": 100.0 * bwd / total if total else 0.0},
    ]
    return {
        "source": "Synthetic_NAF_v2_frozen_validation",
        "data_kind": "simulated_one_minute_flow_aggregates",
        "minute": end_minute,
        "summary": {
            "packets_per_second": float(latest[PPS]),
            "throughput_kib_per_second": float(latest[BPS] / KIB),
            "flows_per_minute": float(latest[FLOW_COUNT]),
            "packets_per_minute": float(latest[TOTAL_PKTS]),
        },
        "traffic": [
            {"minute": int(end_minute - 9 + offset),
             "forward_mib_per_minute": float(row[FWD_BYTES] / MIB),
             "backward_mib_per_minute": float(row[BWD_BYTES] / MIB)}
            for offset, row in enumerate(data)
        ],
        "packet_direction_breakdown": breakdown,
        "h10_risk_history": risk_history,
        "missing_fields": {
            "connections": "Not in the model input features",
            "protocols": "Not in the forecasting replay features",
            "live_monitoring": "No network sensor is connected",
        },
    }


def build_risk_history(indices, minutes, probabilities):
    probs = np.asarray(probabilities, dtype=np.float64)
    if probs.ndim != 2 or probs.shape[1] != 3 or len(indices) != len(probs):
        raise ValueError("Expected one H5/H10/H15 vector per recent decision window")
    return [{"replay_index": int(index), "episode_minute": int(minutes[index]),
             "h10_model_score_percent": float(probs[position, 1] * 100.0)}
            for position, index in enumerate(indices)]
