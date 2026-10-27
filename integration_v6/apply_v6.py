from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import shutil

root = Path(__file__).resolve().parents[1]
kit = Path(__file__).resolve().parent
versions = json.loads((kit / "versions.json").read_text())
files = {
    "frontend/src/App.jsx": "App.jsx",
    "frontend/src/ModelReplayPanel.jsx": "ModelReplayPanel.jsx",
    "frontend/src/ReplayTelemetry.jsx": "ReplayTelemetry.jsx",
    "frontend/src/LiveTrafficPanel.jsx": "LiveTrafficPanel.jsx",
}

def digest(path):
    return sha256(path.read_bytes()).hexdigest()

pending = []
for rel, filename in files.items():
    source = kit / "updates" / filename
    dest = root / rel
    if not dest.is_file() or not source.is_file():
        raise SystemExit(f"[STOP] Missing {rel}. Install the previous Monitor/Settings updates first.")
    current = digest(dest)
    expected = versions["expected_sha256"][filename]
    patched = versions["patched_sha256"][filename]
    if current == patched:
        print(f"[OK] Already updated: {rel}")
        continue
    if current != expected:
        raise SystemExit(f"[STOP] {rel} differs from the known V4/V5 version. No files changed. Your edits are safe.")
    pending.append((dest, source, rel))

css_dest = root / "frontend/src/monitorPolish.css"
css_src = kit / "updates/monitorPolish.css"
if css_dest.exists() and digest(css_dest) != digest(css_src):
    raise SystemExit("[STOP] Custom frontend/src/monitorPolish.css exists. No files changed.")

if not pending and css_dest.exists():
    print("[OK] V6 is already installed.")
    raise SystemExit(0)

backup = root / "integration_v6" / "backups" / datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
for dest, source, rel in pending:
    archive = backup / rel
    archive.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(dest, archive)

for dest, source, rel in pending:
    shutil.copy2(source, dest)
    print(f"[UPDATED] {rel}")

if not css_dest.exists():
    shutil.copy2(css_src, css_dest)
    print("[ADDED] frontend/src/monitorPolish.css")

if pending:
    print(f"[BACKUP] {backup.relative_to(root)}")
print("[SAFE] Original index.css, backend, models, database, Settings, and History untouched.")
print("[NEXT] Reload frontend; backend can stay running.")
