"""Guarded V7 integration; checks all files and backs up edits before changing anything."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
UPDATES = HERE / "updates"
MANIFEST = json.loads((HERE / "versions.json").read_text(encoding="utf-8"))
ROUTE_MARKER = "# NETGUARD_RAG_V7_ROUTE"
APP_TRAILER = "\n\n# NETGUARD_RAG_V7_ROUTE\nfrom rag_bridge import router as rag_router\napi.include_router(rag_router)\n"


def checksum(data):
    return sha256(data).hexdigest()


def main():
    if not (ROOT / "frontend/src/index.css").is_file() or not (ROOT / "backend/app.py").is_file():
        raise SystemExit("[STOP] Install this ZIP into the existing NetGuard project root, not inside rag/ or frontend/.")
    changes = []
    for relative, previous in MANIFEST["expected_original_sha256"].items():
        dest = ROOT / relative
        src = UPDATES / relative
        if not src.is_file() or not dest.is_file():
            raise SystemExit(f"[STOP] Required existing file missing: {relative}. Install V6 and standalone RAG first.")
        current = checksum(dest.read_bytes())
        updated = checksum(src.read_bytes())
        if current == updated:
            continue
        if current != previous:
            raise SystemExit(f"[STOP] {relative} differs from the reviewed source. No files changed. Share it for a safe merge.")
        changes.append((dest, src, relative))

    for relative in MANIFEST["new_files"]:
        dest, src = ROOT / relative, UPDATES / relative
        if not src.is_file():
            raise SystemExit(f"[STOP] Update package is incomplete: {relative}")
        if dest.exists():
            if checksum(dest.read_bytes()) != checksum(src.read_bytes()):
                raise SystemExit(f"[STOP] Custom file already exists: {relative}. No files changed.")
        else:
            changes.append((dest, src, relative))

    backend = ROOT / "backend/app.py"
    original = backend.read_bytes()
    existing = backend.read_text(encoding="utf-8")
    if ROUTE_MARKER not in existing:
        if checksum(original) not in MANIFEST["allowed_backend_app_sha256"]:
            raise SystemExit("[STOP] backend/app.py differs from the reviewed V3/V6 API. No files changed. Share it for a safe merge.")
        if 'api = FastAPI(' not in existing or '@api.get("/api/history/{event_id}")' not in existing:
            raise SystemExit("[STOP] Backend entrypoints have changed. No files changed.")
        changes.append((backend, None, "backend/app.py"))
    elif existing.count(ROUTE_MARKER) != 1 or not existing.rstrip().endswith("api.include_router(rag_router)"):
        raise SystemExit("[STOP] Backend already has an unexpected RAG integration. No files changed.")

    if not changes:
        print("[OK] V7 already installed. No changes made.")
        return
    backup = HERE / "backups" / datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    for dest, src, relative in changes:
        if dest.exists():
            archived = backup / relative
            archived.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest, archived)
    for dest, src, relative in changes:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src is None:
            dest.write_text(existing.rstrip() + APP_TRAILER, encoding="utf-8")
        else:
            shutil.copy2(src, dest)
        print(f"[UPDATED] {relative}")
    if backup.exists():
        print("[BACKUP]", backup.relative_to(ROOT))
    print("[SAFE] Did not alter App.jsx, index.css, models, inference database, rag/.env, or existing Chroma data.")
    print("[NEXT] Reindex knowledge, restart the RAG and main backend processes, refresh frontend.")


if __name__ == "__main__":
    main()
