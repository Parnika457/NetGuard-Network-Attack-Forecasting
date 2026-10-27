# NetGuard Settings + Alerts V4 (apply AFTER V3)

From project root:

```bash
unzip -o ~/Downloads/NetGuard_Settings_Alerts_V4.zip -d .
python integration_v4/apply_v4.py
```

Restart Vite. FastAPI requires no code changes: its `/api/health` already exists.

What changes:
- Replay Controls is a real on/off switch and disables replay inference requests and buttons. Frontend-only cannot make fake predictions.
- Threat Notifications turns ON/OFF **in-app** alerts only for newly completed synthetic replay inferences.
- Threat Sensitivity filters by **Stacked LSTM H10**: LOW <30%, MEDIUM 30-59.99%, HIGH 60-84.99%, CRITICAL >=85%; all activity alerts every newly processed replay window. **These are arbitrarily selected demo UI cutoffs, NOT validated security thresholds or calibrated probabilities.**
- Optional browser desktop notifications require explicit button/permission and only work while the web dashboard is open. No email, SMS, service workers, server push or background alerting.
- Backend Status checks `/api/health` every five seconds and confirms `status=ok` and `models_loaded=true`. When only Vite runs, it says DISCONNECTED; when FastAPI starts it switches to CONNECTED.
- Defense Mode is disabled because there is no automatic defense implementation.

Replay is not live traffic. The live-host mode uses network counters only, with **no attack forecasting**.

## Test
1. Run only Vite (`cd frontend && npm run dev`): Settings must say DISCONNECTED.
2. Start FastAPI with `.venv312` (`python backend/run_api.py`). In ~5 seconds status becomes CONNECTED.
3. Turn Replay Controls OFF: Monitor replay window buttons disable and no new replay POST happens. Re-enable to resume.
4. Turn Threat Notifications ON, choose All activity, and click Next window. An in-page alert should appear. Switching Critical only should filter out low-risk windows.
5. Turn notifications OFF, navigate to a NEW window: no new alert appears.
6. Stop backend: Settings reports DISCONNECTED again after the next poll.

### What this does not do
No background notifications after browser closes; no live cyberattack alerting; no production thresholds or false claims of guaranteed threats. Browser Notifications can be unavailable/denied depending on browser settings.

### Files modified
- frontend/src/App.jsx
- frontend/src/ModelReplayPanel.jsx
- frontend/src/settingsNotifications.css (new)

The installer first compares SHA-256 hashes with original V3 and backs up replaced files. It refuses to overwrite any modified V3 file. `frontend/src/index.css`, models, model releases, validation files, historical inference database and backend are not touched.
