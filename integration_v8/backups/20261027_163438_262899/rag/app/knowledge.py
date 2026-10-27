"""Load local curated guides, user PDFs/MD/TXT and optionally official ATT&CK STIX."""
from __future__ import annotations
from html import unescape
import json
from pathlib import Path
import re
from typing import Iterator

from .chunking import Document

# Public official ATT&CK bundle. Pin a version for repeatable experiments.
MITRE_JSON_URL = (
    "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/"
    "master/enterprise-attack/enterprise-attack-20.0.json"
)


def clean_stix_text(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\[(.*?)\]\((https?://[^)]*)\)", r"\1", s)
    return re.sub(r"\s+", " ", unescape(s)).strip()


def seed_documents(knowledge_dir: Path) -> Iterator[Document]:
    data = json.loads((knowledge_dir / "seed_attack_guides.json").read_text(encoding="utf-8"))
    for entry in data:
        yield Document(
            title=entry["title"], text=entry["text"], source_type="project_guide",
            source_url=None, location="knowledge/seed_attack_guides.json",
            attack_class=entry["attack_class"],
        )


def model_scope_documents(knowledge_dir: Path) -> Iterator[Document]:
    p = knowledge_dir / "model_scope.md"
    if p.exists():
        yield Document("NetGuard model scope and limitations", p.read_text(encoding="utf-8"),
                       "project_documentation", None, "knowledge/model_scope.md")


def user_documents(folder: Path) -> Iterator[Document]:
    """Only ingest explicitly trusted local files, never arbitrary remote/user URLs."""
    if not folder.exists():
        return
    for p in sorted(folder.rglob("*")):
        if not p.is_file() or p.stat().st_size > 20_000_000:
            continue
        if p.suffix.lower() in {".md", ".txt"}:
            text = p.read_text(encoding="utf-8", errors="replace")
            yield Document(p.stem, text, "local_document", None, p.as_posix())
        elif p.suffix.lower() == ".pdf":
            from pypdf import PdfReader
            try:
                reader = PdfReader(str(p))
                for i, page in enumerate(reader.pages, 1):
                    text = page.extract_text() or ""
                    if text.strip():
                        source_url = ("https://csrc.nist.gov/pubs/sp/800/61/r3/final"
                                      if "800-61r3" in p.name.lower() else None)
                        yield Document(p.stem, text, "local_pdf", source_url, f"{p.as_posix()}#page={i}")
            except Exception as exc:
                print(f"Skipping invalid/unreadable PDF {p}: {exc}")


def mitre_documents(stix_path: Path) -> Iterator[Document]:
    raw = json.loads(stix_path.read_text(encoding="utf-8"))
    allowed = {"attack-pattern": "techniques", "course-of-action": "mitigations"}
    for item in raw.get("objects", []):
        kind = allowed.get(item.get("type"))
        if not kind or item.get("revoked") or item.get("x_mitre_deprecated"):
            continue
        reference = next((ref for ref in item.get("external_references", [])
                          if ref.get("source_name") == "mitre-attack" and ref.get("external_id")), None)
        if reference is None:
            continue
        code = reference["external_id"]
        title = f"MITRE ATT&CK {code}: {item.get('name', 'Unnamed')}"
        desc = clean_stix_text(item.get("description", ""))
        if len(desc) < 50:
            continue
        url = reference.get("url") or f"https://attack.mitre.org/{kind}/{code}/"
        yield Document(title, desc[:10000], "mitre_attack", url,
                       f"ATT&CK v20.0/{code}", "general")
