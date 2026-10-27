# NetGuard V8 — Prediction-aware RAG and grounded references

**This is an overlay for a working V7 NetGuard project.** It modifies existing files,
not a new RAG service. Do not copy a new frontend, recreate your database, or retrain models.

## Files changed

Existing (10): `rag/app/{chunking,knowledge,ingest,schemas,retriever,service,llm}.py`,
`backend/rag_bridge.py`, `frontend/src/RagAnalysis.jsx`,
`frontend/src/ragAnalysis.css`.

New (2): `rag/knowledge/official_reference_summaries.json`,
`integration_v8/tests/test_v8_contract.py`.

Unchanged: `frontend/src/App.jsx`, `frontend/src/index.css`,
`frontend/src/ModelReplayPanel.jsx`, `frontend/src/HistoryView.jsx`,
`backend/app.py`, trained weights/scalers, `.env`, RAG venv, and Chroma files.

The new reference file consists of **NetGuard-authored summaries** linked to verified
primary NIST/MITRE web pages. These are not full copies of official publications and
must not be described as such. `FUZZING` uses project guidance, not a fake MITRE mapping.

## Installation (from project root)

1. Stop the existing RAG service on port 8001 (`Ctrl+C`) before reindexing.
2. Extract the ZIP to the project root and run the guarded installer:

   ```bash
   unzip -o ~/Downloads/NetGuard_RAG_Quality_V8.zip -d .
   .venv312/bin/python integration_v8/apply_v8.py
   ```

3. Rebuild the RAG index so new references and family metadata are included:

   ```bash
   cd rag
   source .venv/bin/activate
   python -m app.ingest
   python -m pytest -q
   python -m pytest -q ../integration_v8/tests
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
   ```

4. Open another terminal, start/restart the main NetGuard backend:

   ```bash
   cd ~/Downloads/Network-Attack-Forecasting-Project-main
   source .venv312/bin/activate
   python backend/run_api.py
   ```

5. Refresh the Vite frontend. The existing Explain Prediction and Analyze Prediction
   buttons show the improved UI. No `npm install` is required.

## Expected behavior

- An analysis of a saved replay uses that saved H5/H10/H15 and conditional family/ETA.
- The RAG backend receives actual **synthetic replay** aggregate metrics if available;
  it never calls them measured live telemetry or model explanations (no SHAP was run).
- The panel shows a compact saved-value summary, targeted investigation, and
  expandable, unique citations with real links where applicable.
- If a Gemini request fails, the original dashboard and model forecasts remain usable.
- This does not claim that forecast thresholds are calibrated or attacks confirmed.

## Troubleshooting

If installer displays `[STOP]`, it deliberately changed nothing. Do not force copy.
This means your working files differ from the exact reviewed V7 versions; share the
STOP output for a safe merge.

If the API responds with an old explanation or an HTTP 422 contract error, restart
both Python servers and recheck that RAG index ingestion finished. For browser
changes, hard refresh Cmd+Shift+R. If errors persist, inspect the backend terminal.

## Quality verification

Unit tests cover exact record values, synthetic-vs-live separation, source URL
provenance, future-family retrieval, distinct doc citations, and existing V7 routes.
Provider generation must be verified by clicking both buttons on your Mac; we don't
have access to your secret key or live services in the packaging environment.
