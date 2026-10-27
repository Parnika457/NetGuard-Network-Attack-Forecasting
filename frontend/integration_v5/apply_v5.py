from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCE = HERE / "updates"
DEST = ROOT / "frontend" / "src"
HISTORY = DEST / "HistoryView.jsx"
STYLE = DEST / "historyView.css"
ORIGINAL_SHA = "a917beb03097807a23426624ad9580f3c86c13c7ec9f7570ca1f8b3d99b89ad9"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def run():
    if not (ROOT / "frontend" / "src" / "App.jsx").is_file():
        raise SystemExit("[STOP] Run this installer from the NetGuard project root.")
    if not HISTORY.is_file():
        raise SystemExit("[STOP] Missing frontend/src/HistoryView.jsx.")
    update_history = SOURCE / "HistoryView.jsx"
    update_style = SOURCE / "historyView.css"
    existing = digest(HISTORY)
    updated = digest(update_history)
    if existing == updated and STYLE.exists() and digest(STYLE) == digest(update_style):
        print("[PASS] History polish V5 is already installed. No changes made.")
        return
    if existing != ORIGINAL_SHA:
        raise SystemExit("[STOP] HistoryView.jsx has other edits. Nothing changed. Please share that file to prepare a safe merge.")
    if STYLE.exists() and digest(STYLE) != digest(update_style):
        raise SystemExit("[STOP] historyView.css already exists with different content. Nothing changed.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    backup = HERE / "backups" / stamp
    backup.mkdir(parents=True, exist_ok=False)
    shutil.copy2(HISTORY, backup / "HistoryView.jsx")
    shutil.copy2(update_history, HISTORY)
    shutil.copy2(update_style, STYLE)
    print("[PASS] Updated HistoryView.jsx and added historyView.css")
    print("[PASS] Original HistoryView.jsx backed up at:", backup)
    print("[UNCHANGED] App.jsx, index.css, backend, model weights and database")


if __name__ == "__main__":
    run()
