"""Simple deterministic, overlap-aware word chunking (no framework dependency)."""
import hashlib
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Document:
    title: str
    text: str
    source_type: str
    source_url: str | None
    location: str
    attack_class: str = "general"


@dataclass(frozen=True)
class Chunk:
    id: str
    text: str
    metadata: dict


def split_document(doc: Document, max_words: int = 240, overlap_words: int = 40) -> list[Chunk]:
    if not (max_words > overlap_words >= 0):
        raise ValueError("max_words must exceed non-negative overlap_words")
    words = re.findall(r"\S+", re.sub(r"\s+", " ", doc.text).strip())
    if not words:
        return []
    stem = hashlib.sha256((doc.source_type + "|" + doc.location + "|" + doc.title).encode()).hexdigest()[:20]
    chunks = []
    step = max_words - overlap_words
    for offset in range(0, len(words), step):
        part = words[offset:offset + max_words]
        text = f"{doc.title}\n" + " ".join(part)
        chunks.append(Chunk(
            id=f"{stem}-{offset:06d}",
            text=text,
            metadata={
                "title": doc.title,
                "source_type": doc.source_type,
                "source_url": doc.source_url or "",
                "location": doc.location,
                "attack_class": doc.attack_class,
                "doc_id": stem,
            },
        ))
        if offset + max_words >= len(words):
            break
    return chunks
