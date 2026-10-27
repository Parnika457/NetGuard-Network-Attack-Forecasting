"""Guarded, idempotent upgrade from the exact reviewed V7 file versions."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
UPDATES = HERE / "updates"
MANIFEST = json.loads((HERE / "versions.json").read_text(encoding="utf-8"))


def digest(p: Path) -> str:
    return sha256(p.read_bytes()).hexdigest()


def main():
    if not (ROOT / "frontend/src/index.css").is_file() or not (ROOT / "backend/app.py").is_file():
        raise SystemExit("[STOP] Run from the existing NetGuard project root (V7 required).")
    app = (ROOT / "backend/app.py").read_text(encoding="utf-8")
    if "NETGUARD_RAG_V7_ROUTE" not in app:
        raise SystemExit("[STOP] V7 RAG backend is not installed. No changes made.")

    changes = []
    for relative, expected in MANIFEST["expected_v7_sha256"].items():
        dest = ROOT / relative
        src = UPDATES / relative
        if not dest.is_file() or not src.is_file() or digest(src) != MANIFEST["target_v8_sha256"][relative]:
            raise SystemExit(f"[STOP] Missing or incomplete package file: {relative}. No changes made.")
        if digest(dest) == digest(src):
            continue
        if digest(dest) != expected:
            raise SystemExit(f"[STOP] {relative} differs from the reviewed V7 version. No files changed. Request a safe merge.")
        changes.append((relative, dest, src))

    for relative, expected in MANIFEST["new_files"].items():
        dest = ROOT / relative
        src = UPDATES / relative
        if not src.is_file() or digest(src) != expected:
            raise SystemExit(f"[STOP] Package file is missing or damaged: {relative}. No changes made.")
        if dest.exists():
            if not dest.is_file() or digest(dest) != expected:
                raise SystemExit(f"[STOP] Existing custom file conflicts with {relative}. No files changed.")
        else:
            changes.append((relative, dest, src))

    if not changes:
        print("[OK] NetGuard RAG V8 already installed. Nothing changed.")
        return

    backup = HERE / "backups" / datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    for relative, dest, src in changes:
        if dest.is_file():
            archived = backup / relative
            archived.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest, archived)
    for relative, dest, src in changes:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        print(f"[UPDATED] {relative}")
    if backup.exists():
        print("[BACKUP]", backup.relative_to(ROOT))
    print("[SAFE] App.jsx, index.css, predictions, models, database, rag/.env and theme unchanged.")
    print("[NEXT] Reindex RAG and restart RAG + NetGuard backend.")


if __name__ == "__main__":
    main()
