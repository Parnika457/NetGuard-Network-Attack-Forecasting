# NetGuard Monitor V6 — UI polish and toast alerts

Uses your existing V4 Settings, V5 History, V3 Live/Replay switch. Only the four Monitor-facing React components and a new CSS file are affected.

## Install

From the project root in VS Code:

```bash
unzip -o ~/Downloads/NetGuard_Monitor_Toast_V6.zip -d .
python integration_v6/apply_v6.py
cd frontend && npm run dev
```

An SHA-256 guarded installer checks all existing source files **before editing anything**. If any differ from the expected V4/V5 versions, it stops without replacing them. Existing changed files are automatically backed up to `integration_v6/backups/`.

## Changes

- Removes repeated explanation text from the Monitor/Forecast/Telemetry screen; preserves existing dark/light colors and charts.
- Keeps one visible synthetic replay source indication in the mode selector and telemetry title.
- Model scores, conditional family/ETA, backend connectivity, history persistence, and traffic feature calculations are unchanged.
- Notification is a floating, dismissible top-right toast; disappears after 7 seconds. No sound, alarm, or new dependency.
- Existing Settings sensitivity levels still control alerts: Medium (H10 >= 30%), High (>= 60%), Critical (>= 85%); All activity shows every newly processed replay. Notification toggle must be on. Thresholds remain research-demo defaults, not calibrated live security alerts.
- Optional browser desktop alerts still respect the same filter if already enabled.

## Test

Run both services, enable Threat Notifications in Settings, select **High & Critical**, and replay a high-H10 sample (for example one already known from your History with H10 >= 60%). The toast should appear at top-right. Replaying a below-60% new window should not produce a toast.

Select All activity if you want an alert for every newly processed replay window.

If only React is running, Settings still shows DISCONNECTED, and no prediction notifications will be triggered.
