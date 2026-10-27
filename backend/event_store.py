"""SQLite audit log of actual NetGuard inference requests (NOT confirmed attacks)."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3

DB_PATH = Path(__file__).resolve().parent / "data" / "inference_history.sqlite3"


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    with _connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS inference_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_utc TEXT NOT NULL,
                event_type TEXT NOT NULL,
                mode TEXT NOT NULL,
                model_release TEXT NOT NULL,
                dataset TEXT,
                replay_index INTEGER,
                episode_id TEXT,
                episode_minute INTEGER,
                result_json TEXT NOT NULL,
                UNIQUE(event_type, model_release, dataset, replay_index)
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_events_time ON inference_events(id DESC)")


def _save(payload, event_type):
    timestamp = datetime.now(timezone.utc).isoformat()
    mode = payload["mode"]
    release = payload["model_release"]
    dataset = payload.get("dataset")
    replay_index = payload.get("index")
    episode_id = payload.get("episode_id")
    episode_minute = payload.get("episode_minute")
    values = (timestamp, event_type, mode, release, dataset, replay_index,
              episode_id, episode_minute, json.dumps(payload, allow_nan=False))
    with _connect() as db:
        # Revisited replay indices update their recorded timestamp/result, not duplicate rows.
        if replay_index is not None:
            db.execute("""
                INSERT INTO inference_events
                    (created_utc, event_type, mode, model_release, dataset,
                     replay_index, episode_id, episode_minute, result_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(event_type, model_release, dataset, replay_index)
                DO UPDATE SET created_utc=excluded.created_utc,
                              result_json=excluded.result_json
            """, values)
            row = db.execute("""SELECT id, created_utc FROM inference_events
                WHERE event_type=? AND model_release=? AND dataset=? AND replay_index=?""",
                (event_type, release, dataset, replay_index)).fetchone()
        else:
            cursor = db.execute("""
                INSERT INTO inference_events
                    (created_utc, event_type, mode, model_release, dataset,
                     replay_index, episode_id, episode_minute, result_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, values)
            row = db.execute("SELECT id, created_utc FROM inference_events WHERE id=?",
                             (cursor.lastrowid,)).fetchone()
    return dict(row)


def save_forecast_event(payload):
    return _save(payload, "FORECAST_INFERENCE")


def save_detection_event(payload):
    # Stores model output only, never raw source flow feature values.
    return _save(payload, "DETECTION_INFERENCE")


def _parse(row):
    entry = dict(row)
    entry["prediction"] = json.loads(entry.pop("result_json"))
    return entry


def list_events(limit, offset):
    with _connect() as db:
        rows = db.execute("SELECT * FROM inference_events ORDER BY created_utc DESC, id DESC LIMIT ? OFFSET ?",
                          (limit, offset)).fetchall()
        total = db.execute("SELECT COUNT(*) FROM inference_events").fetchone()[0]
    return {"items": [_parse(row) for row in rows], "total": total,
            "limit": limit, "offset": offset,
            "next_offset": offset + limit if offset + limit < total else None,
            "note": "Recorded inference requests, NOT verified attack incidents."}


def get_event(event_id):
    with _connect() as db:
        row = db.execute("SELECT * FROM inference_events WHERE id=?", (event_id,)).fetchone()
    return _parse(row) if row else None
