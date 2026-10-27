from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
import json, shutil

ROOT = Path(__file__).resolve().parents[1]
KIT = Path(__file__).resolve().parent
meta = json.loads((KIT / "versions.json").read_text())
locations = {
    "frontend/src/App.jsx": "App.jsx",
    "frontend/src/ModelReplayPanel.jsx": "ModelReplayPanel.jsx",
}

# Validate ALL files before changing ANY. Never overwrite user-edited source.
todo = []
for rel, source_name in locations.items():
    dest = ROOT / rel
    source = KIT / "updates" / source_name
    if not dest.is_file() or not source.is_file():
        raise SystemExit(f"Missing {rel} or kit file; ensure V3 is already installed")
    current = sha256(dest.read_bytes()).hexdigest()
    if current == meta["patched_v4_sha256"][rel]:
        print(f"[PASS] Already V4: {rel}")
        continue
    if current != meta["expected_v3_sha256"][rel]:
        raise SystemExit(f"[STOP] {rel} differs from the V3 kit. No files changed. Send its sha256 instead of overwriting your edits.")
    todo.append((dest, source, rel))

css_dest = ROOT / "frontend/src/settingsNotifications.css"
css_src = KIT / "updates/settingsNotifications.css"
if css_dest.exists() and css_dest.read_bytes() != css_src.read_bytes():
    raise SystemExit("[STOP] Custom settingsNotifications.css exists; no files changed")

if not todo and css_dest.exists():
    print("[PASS] NetGuard V4 already installed; nothing changed")
    raise SystemExit(0)
backup = ROOT / "integration_v4/backups" / datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
for dest, source, rel in todo:
    target = backup / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(dest, target)
for dest, source, rel in todo:
    shutil.copy2(source, dest)
    print(f"[UPDATED] {rel}")
if not css_dest.exists():
    shutil.copy2(css_src, css_dest)
    print("[ADDED] frontend/src/settingsNotifications.css")
print(f"[BACKUP] {backup.relative_to(ROOT)}")
print("[SAFE] index.css, backend, database and frozen models are untouched")
print("[NEXT] Restart Vite; backend can remain running. Test Settings with backend on/off.")
