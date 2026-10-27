"""Read local host interface counters only; no packet capture, no ML inference.

This reads operating-system I/O counters on the machine running FastAPI.
It cannot attribute traffic to flows, protocols, attacks, or other devices.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone

import psutil

_LOCK = threading.Lock()
_LAST = {}
_EXCLUDED_PREFIXES = ("lo", "awdl", "llw", "utun", "p2p", "bridge", "vmenet", "gif", "stf", "anpi")


def _active_names():
    stats = psutil.net_if_stats()
    counters = psutil.net_io_counters(pernic=True, nowrap=True)
    names = [name for name, item in stats.items() if item.isup and name in counters]
    names.sort(key=lambda name: (
        name.startswith(_EXCLUDED_PREFIXES),
        not name.startswith(("en", "eth", "wlan", "wl", "eno", "ens")),
        name,
    ))
    return names, counters


def available_interfaces():
    names, _ = _active_names()
    preferred = next((n for n in names if not n.startswith(_EXCLUDED_PREFIXES)), None)
    if preferred is None and names:
        preferred = names[0]
    return {"interfaces": names, "default_interface": preferred,
            "capture_type": "host_interface_counters", "requires_packet_capture": False,
            "models_operating_on_live_data": False}


def read_interface(name: str | None = None):
    names, counters = _active_names()
    if not names:
        raise ValueError("No active network interface with readable counters")
    name = name or available_interfaces()["default_interface"]
    if name not in names:
        raise ValueError("Selected interface is missing or not active")

    counter = counters[name]
    now = time.monotonic()
    snapshot = (now, int(counter.bytes_recv), int(counter.bytes_sent),
                int(counter.packets_recv), int(counter.packets_sent))
    with _LOCK:
        previous = _LAST.get(name)
        _LAST[name] = snapshot

    rates = None
    if previous:
        elapsed = now - previous[0]
        # Ignore overly close calls or a sleep/resume gap.
        if 0.25 <= elapsed <= 20:
            rates = {
                "inbound_bytes_per_second": max(0.0, (snapshot[1] - previous[1]) / elapsed),
                "outbound_bytes_per_second": max(0.0, (snapshot[2] - previous[2]) / elapsed),
                "inbound_packets_per_second": max(0.0, (snapshot[3] - previous[3]) / elapsed),
                "outbound_packets_per_second": max(0.0, (snapshot[4] - previous[4]) / elapsed),
            }
    return {
        "mode": "live_host_telemetry",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "interface": name,
        "sampling_ready": rates is not None,
        "rates": rates,
        "counters": {
            "received_bytes_total": snapshot[1],
            "sent_bytes_total": snapshot[2],
            "received_packets_total": snapshot[3],
            "sent_packets_total": snapshot[4],
        },
        "models_operating_on_live_data": False,
        "notes": "Host interface counters only; no flow features, attack predictions, protocol distribution, or whole-LAN visibility.",
    }
