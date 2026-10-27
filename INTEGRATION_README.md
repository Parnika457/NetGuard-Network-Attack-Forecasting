# NetGuard V1 — first frontend/backend integration slice

This is an **overlay** for your existing `Network-Attack-Forecasting-Project-main/` project.
It does not overwrite model weights, `backend/netguard_models.py`, your frozen release,
existing test reports, or `frontend/src/data/mockData.jsx`.

## Before extracting

Make a Git commit or copy your existing `frontend/src/App.jsx` and `frontend/vite.config.js` as a backup.
The kit replaces **only** these two existing files, and adds `frontend/src/ModelReplayPanel.jsx`,
`frontend/src/modelReplayPanel.css`, `backend/app.py`, `backend/run_api.py`, and
`backend/requirements_api.txt`.

## Install overlay from your project root (VS Code terminal on Mac)

```bash
unzip -o ~/Downloads/NetGuard_V1_Integration_Starter.zip -d .
source .venv312/bin/activate
python -m pip install -r backend/requirements_api.txt
```

## Terminal 1 — start FastAPI

```bash
python backend/run_api.py
```

Open `http://127.0.0.1:8000/docs` for Swagger and `http://127.0.0.1:8000/api/health` for health.
The backend loads all three frozen model checkpoints after checking every frozen hash.
It reads `backend/validation_data/windows_W10_VALIDATION.npz` to support replay.
Do **not** run with multiple workers or auto-reload yet; macOS numerical libraries
were stable with single-thread limits.

## Terminal 2 — run Vite

```bash
cd frontend
npm install
npm run dev
```

Open the local URL Vite prints (normally `http://localhost:5173/`). Vite forwards `/api` to FastAPI.
The new model panel appears at the top of Monitor with forecast probabilities, family, and
conditional ETA. Click Previous/Next/Jump to replay additional frozen synthetic windows.

## Smoke test

```bash
curl http://127.0.0.1:8000/api/health
curl 'http://127.0.0.1:8000/api/replay/forecast?index=0'
```

`POST /api/forecast` accepts `{"window": [[14 numeric values] ...10 rows]}`.
`POST /api/detect` accepts `{"features": {42 flow features}, "threshold": 0.5}`.
The detection threshold 0.5 is an exploratory default; no operational alert policy is calibrated.

## Honest data-source labels

- Stacked LSTM: H5/H10/H15 predictions from **simulated** validation windows.
- Competing-risk LSTM: attack family and conditional time-to-onset on same windows.
- Weighted XGBoost: **separate** flow record endpoint; not auto-populated from synthetic replay.
- Other existing dashboard traffic charts and history records remain illustrative **static samples**.
- No real packet capture, live monitoring, auto-blocking, authentication, notifications,
  RAG or event-storage integration is included in this first slice.
- The API intentionally does not read TEST labels or return ground-truth onset labels.

## Safety and reproducibility

Keep `.venv/`, `.venv312/`, `node_modules/`, `backend/validation_data/`, and local `.env`
files out of Git. The archive contains **no raw datasets or trained weights**.
Run `git diff` before committing changes. Keep the frozen release JSON unchanged.
