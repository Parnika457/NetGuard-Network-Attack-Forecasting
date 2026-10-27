# NetGuard V9 — Final RAG analysis display polish

Overlay for an existing **V8 installation**. It changes only 3 existing files:
`rag/app/llm.py`, `frontend/src/RagAnalysis.jsx`, and `frontend/src/ragAnalysis.css`.

No changes to `frontend/src/App.jsx`, `frontend/src/index.css`,
`frontend/src/HistoryView.jsx`, `frontend/src/ModelReplayPanel.jsx`,
`backend/app.py`, `backend/rag_bridge.py`, user accounts, model artifacts,
SQLite history, `rag/.env`, or the Chroma index.

## Installation

From your project root (Python 3.12 in `.venv312`):

```bash
unzip -o ~/Downloads/NetGuard_RAG_Final_Polish_V9.zip -d .
.venv312/bin/python integration_v9/apply_v9.py
```

The installer checks all hashes **before** writing anything and saves backups.
If it prints `[STOP]`, do not force overwrite; current files need an exact merge.

Then restart your RAG service (port 8001):

```bash
cd rag
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

There is **no new reference content** and the embedding model is unchanged,
so re-running `python -m app.ingest` is unnecessary.

Keep your existing main backend (port 8000) and frontend (Vite) running.
Refresh the browser (`Cmd+Shift+R`) to load the new React UI.

## Result

- The displayed forecast assessment uses exact saved percentages from the
  `prediction_context` returned by the main backend, not Gemini prose.
- The separate attack-family confidence and ETA always remain conditional.
- Forecast and current-detection assessments are clear and specific, without
  repeated model-architecture paragraphs.
- Gemini still generates targeted investigation steps, grounded in relevant
  retrieved cybersecurity research summaries. It may still be wrong and should
  be evaluated before making research accuracy claims.
- References show one clickable title per unique cited source and one **plain
  non-clickable** research-summary metadata line.
- Source summaries link to official NIST and MITRE publications; retrieved
  text is still authored by NetGuard, not the official full texts.

No changes to the original dashboard theme or chart design.
