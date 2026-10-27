# NetGuard Monitor + History V2 (overlay on V1 Integration Starter)

All values on the Monitor page now originate from the SAME frozen synthetic validation replay window used for model inference; there are **no hardcoded sample metrics, protocol percentages, connection counts, risk bars, or history entries**.

## Extract from your VS Code project root

1. Stop the existing FastAPI and Vite servers (Ctrl+C each).
2. Back up `backend/app.py`, `frontend/src/App.jsx`, and `frontend/src/ModelReplayPanel.jsx` or commit them to a local git branch.
3. `unzip -o ~/Downloads/NetGuard_Monitor_History_V2.zip -d .`
4. Run `source .venv312/bin/activate` if needed.
5. Start backend: `python backend/run_api.py` (unchanged; it sets safe native thread limits).
6. Start frontend in second terminal: `cd frontend && npm run dev`.
7. Visit Monitor, navigate windows, then History.

## New APIs

- `POST /api/replay/step?index=0` computes real frozen-model inference and saves the replayed inference to SQLite; revisiting the same index updates one row rather than duplicating.
- `GET /api/replay/forecast?index=0` remains read-only and now returns telemetry too.
- `GET /api/history?limit=50&offset=0` returns saved inferences, newest first; supports paging.
- `GET /api/history/{id}` fetches an inference detail.
- `POST /api/detect` continues to accept 42-feature UNSW-NB15 flows and now records the model *output* (not the raw input record).

### Database location

`backend/data/inference_history.sqlite3` is created automatically on the first backend launch.
Add the line `backend/data/` to the root `.gitignore` (along with `.venv312/`, `backend/validation_data/`, and `node_modules/`). Do not commit this local SQLite file, source traffic, or raw datasets.

### Semantics

- `Packets_Per_Second`, `Bytes_Per_Second`, `Flow_Count`, `Total_Packets`, forward/backward packets and bytes come from the 14-feature simulated validation input. Byte *sum* values are per 1-minute episode step; charts show MiB/min. A "packet direction" pie is not a protocol-distribution pie.
- H10 history bars come from actual stacked LSTM predictions on recent **same-episode** decision windows. They are *not* an operational alert history.
- Historical rows represent **inference executions**, not independently verified cyberattack incidents. Detection and forecasting remain separate data pipelines.
- No live traffic, protocols, unique connection count, RAG evidence, alert thresholds, automatic blocking or login are implemented in this overlay.
- The current mode is `synthetic_validation_replay`; never use the word `LIVE` for it.

## Quick API smoke checks

`curl http://127.0.0.1:8000/api/health`

`curl -X POST 'http://127.0.0.1:8000/api/replay/step?index=0'`

`curl 'http://127.0.0.1:8000/api/history?limit=3'`

All frozen model weights and validation reports remain untouched. No TEST split is loaded. No model is retrained.
