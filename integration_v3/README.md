# NetGuard V3 — H10 precision fix + traffic-source selector

**Prerequisite:** The Monitor + History V2 overlay already runs successfully. This kit does not include or change any frozen model weights.

## Install on Mac (VS Code)

Stop the backend and Vite first (`Ctrl+C` in each terminal). Save the zip to Downloads. At the project root:

```bash
unzip -o ~/Downloads/NetGuard_Mode_H10_V3.zip -d .
source .venv312/bin/activate
python -m pip install -r backend/requirements_live.txt
python integration_v3/apply_v3.py
```

`apply_v3.py` checks for the exact V2 code blocks before writing. It creates timestamped backups under `integration_v3/backups/`. If the files have changed since V2, it stops rather than risk clobbering your edits. **Your original index.css is never replaced.**

Then restart the servers in separate terminals:

```bash
# Terminal 1, project root
source .venv312/bin/activate
python backend/run_api.py

# Terminal 2, project root
cd frontend
npm run dev
```

Visit Monitor. It now offers:
- **Synthetic model replay (default):** model predictions on the frozen synthetic validation dataset, with a readable H10 line chart and correct tiny values.
- **Live Mac traffic:** real OS upload/download and packet rates from one active network interface, without special packet-capture privileges. Switching to live pauses collection until you toggle the top-right status switch ON. You can change interface while paused. Switching back to replay resumes the synthetic model panel.

The live traffic mode **does not** provide attack classification, forecasts, risk percentages, ETA or protocol percentages: that needs a separately engineered and validated 42-feature detector / 10×14 minute-window capture-and-aggregation pipeline. This is not all devices on the Wi-Fi, only traffic visible to the Mac host.

`GET /api/live/interfaces` and `GET /api/live/metrics?interface=en0` are local-backend endpoints. The API listens on 127.0.0.1 only. The live sensor reads interface counters, not packet payloads.

## Version control

Add to your repo root `.gitignore`:

```gitignore
integration_v3/backups/
.venv/
.venv312/
backend/data/
backend/validation_data/
frontend/node_modules/
```

No model weights, release manifests or stored inference history are changed by this upgrade.
