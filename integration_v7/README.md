# NetGuard V7 — Integrated forecast/detection explanations

This patch adds two buttons to the **existing** UI without changing App.jsx, index.css, colors, existing headings, model code, or SQLite history:
- Monitor > Attack forecast > Explain Prediction
- History > Open a saved forecast or detection > Analyze Prediction

Both buttons call `POST /api/rag/explain/history/{event_id}` on the **main FastAPI backend**, which reads the actual saved prediction from SQLite and forwards a restricted schema to the independently running `rag/` service on port 8001.

The new RAG contract preserves:
- Stacked LSTM H5/H10/H15 probabilities for **any onset** (5/10/15 minutes)
- Competing-risk **conditional** future family and its probability, and conditional ETA **given onset within 15 minutes**
- The distinct present-detection class vocabulary

It never turns conditional-family confidence into an unconditional attack probability, never combines outputs of separate models, and never generates additional model predictions. No raw packet capture or live model inference is added.

## Install

From the existing project root containing `backend/`, `frontend/`, `rag/`:

```bash
unzip -o ~/Downloads/NetGuard_RAG_Integration_V7.zip -d .
python integration_v7/apply_v7.py
```

The installer checks the expected V6 frontend, V5 History, V3 backend, and original standalone RAG code, creating backups. If it finds unexpected modifications, it STOPS without overwriting them. Do not force-replace manually.

### Terminal 1 — RAG (port 8001)

```bash
cd rag
source .venv/bin/activate
python -m app.ingest
python -m pytest -q
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

`python -m app.ingest` adds the NetGuard forecast-analysis guide to the existing knowledge base and rebuilds the current Chroma index. It does NOT reset your `.env` or affect trained model files. Verify `rag/.env` still has `GEMINI_MODEL=gemini-3.5-flash-lite` (the model that worked for you).

### Terminal 2 — Main backend (port 8000)

```bash
cd ~/Downloads/Network-Attack-Forecasting-Project-main
source .venv312/bin/activate
python backend/run_api.py
```

### Terminal 3 — Frontend (port 5173)

```bash
cd ~/Downloads/Network-Attack-Forecasting-Project-main/frontend
npm run dev
```

### Test

1. Monitor > Synthetic model replay > select a saved replay window > **Explain Prediction**.
2. History > open that replay > **Analyze Prediction**. It should describe the same saved model values.
3. History > open any saved current-detection inference > **Analyze Prediction**.
4. Stop the RAG server. The prediction dashboard should still work; clicking Explain Prediction shows a contained error (not a broken page).

You can test the main backend RAG endpoint directly using a known saved history ID from `http://127.0.0.1:8000/api/history`:

```bash
curl -sS -X POST http://127.0.0.1:8000/api/rag/explain/history/1 | python -m json.tool
```

(The ID `1` is an example; use an existing ID.)

## Expected limitations

- RAG generation requires internet connectivity and working Gemini API access; it may return provider 503 during demand spikes.
- Models are tested on **synthetic validation replay**, not calibrated for live traffic.
- The included knowledge guide is project-authored. Add authoritative official sources and run a larger evaluation before claiming evidence-backed research quality.
- Login/signup, real packet-to-feature live inference, and automatic defense are **not** implemented by this kit.
