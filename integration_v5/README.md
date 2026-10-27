# NetGuard History V5 — layout polish only

This update edits `frontend/src/HistoryView.jsx` and adds `frontend/src/historyView.css`.

It does not change your model files, inference logic, history database, settings, or `index.css`.

## Setup (project root, VS Code terminal)

1. Place `NetGuard_History_Polish_V5.zip` in `~/Downloads`.
2. From the `Network-Attack-Forecasting-Project-main/` folder:

   ```bash
   unzip -o ~/Downloads/NetGuard_History_Polish_V5.zip -d .
   python integration_v5/apply_v5.py
   ```

3. Restart Vite if needed (`cd frontend && npm run dev`).

The installer verifies the original History component file before replacing it and backs it up under `integration_v5/backups/`. If that file was manually edited, the installer stops without overwriting it.

## Changes

- Compact records with replay index, conditional attack-family label, recorded time, and H10 probability.
- Detailed view with H5/H10/H15, conditional family and ETA, and clean metadata section.
- Small probability values render as `<0.1%` instead of a misleading rounded `0.0%`.
- Removed the repeated interpretation paragraph.
- Existing History API, stored SQLite predictions, and navigation remain intact.
