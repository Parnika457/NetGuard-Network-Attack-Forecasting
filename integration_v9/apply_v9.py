"""Safe, repeatable NetGuard V8 -> V9 RAG presentation and prompt polish."""
import json
import shutil
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
UPDATES = HERE / "updates"
MANIFEST = json.loads((HERE / "versions.json").read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main():
    if not (ROOT / "frontend/src/index.css").is_file() or not (ROOT / "backend/app.py").is_file():
        raise SystemExit("[STOP] Run this from your existing NetGuard project root.")
    if "NETGUARD_RAG_V7_ROUTE" not in (ROOT / "backend/app.py").read_text(encoding="utf-8"):
        raise SystemExit("[STOP] The RAG backend integration is missing. No files changed.")
    changes = []
    for rel, expected in MANIFEST["expected_v8_sha256"].items():
        dest, src = ROOT / rel, UPDATES / rel
        if not dest.is_file() or not src.is_file() or digest(src) != MANIFEST["target_v9_sha256"][rel]:
            raise SystemExit(f"[STOP] Missing or damaged package file: {rel}. No changes made.")
        if digest(dest) == digest(src):
            continue
        if digest(dest) != expected:
            raise SystemExit(f"[STOP] {rel} differs from the reviewed V8 version. No files changed. Do not force overwrite.")
        changes.append((rel, dest, src))
    if not changes:
        print("[OK] NetGuard RAG V9 is already installed. Nothing changed.")
        return
    backup = HERE / "backups" / datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    for rel, dest, src in changes:
        archived = backup / rel
        archived.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dest, archived)
    for rel, dest, src in changes:
        shutil.copy2(src, dest)
        print(f"[UPDATED] {rel}")
    print("[BACKUP]", backup.relative_to(ROOT))
    print("[SAFE] Main theme, App.jsx, model code, backend endpoints, trained weights, knowledge index and RAG .env untouched.")
    print("[NEXT] Restart RAG on 8001; refresh the React frontend. Reindexing is not needed.")


if __name__ == "__main__":
    main()
