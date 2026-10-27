"""CLI: python -m app.ingest [--download-mitre] [--mitre-file PATH]"""
import argparse
import json
from pathlib import Path
import requests
from .chunking import split_document
from .config import get_settings
from .embeddings import Embeddings
from .knowledge import MITRE_JSON_URL, seed_documents, model_scope_documents, user_documents, mitre_documents
from .store import VectorStore


def download_mitre(destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    print("Downloading official MITRE ATT&CK v20.0 STIX bundle (large file)...")
    with requests.get(MITRE_JSON_URL, stream=True, timeout=120) as response:
        response.raise_for_status()
        with destination.open("wb") as output:
            for block in response.iter_content(chunk_size=1024 * 1024):
                if block:
                    output.write(block)
    return destination


def build_index(mitre_file: Path | None, include_documents: Path | None, download: bool) -> int:
    settings = get_settings()
    documents = list(seed_documents(settings.knowledge_dir))
    documents += list(model_scope_documents(settings.knowledge_dir))
    folder = include_documents if include_documents is not None else settings.knowledge_dir / "documents"
    documents += list(user_documents(folder))
    if download:
        mitre_file = download_mitre(settings.data_dir / "downloads" / "enterprise-attack-20.0.json")
    if mitre_file:
        print("Reading MITRE STIX:", mitre_file)
        documents += list(mitre_documents(mitre_file))
    chunks = [c for document in documents for c in split_document(document)]
    if not chunks:
        raise ValueError("No documents found for indexing")
    print(f"Documents: {len(documents)} | chunks: {len(chunks)}")
    embed = Embeddings(settings.embedding_model)
    # Embed all before replacing the current index, so downloading/model errors do not wipe it.
    vectors = []
    for start in range(0, len(chunks), 64):
        vectors += embed.encode([c.text for c in chunks[start:start + 64]])
        print(f"Embedded {min(start + 64, len(chunks))}/{len(chunks)}", end="\r")
    print()
    store = VectorStore(settings.data_dir, settings.chroma_collection, settings.embedding_model, allow_rebuild=True)
    store.reset()
    store.upsert(chunks, vectors)
    store.write_manifest(store.count())
    print("Index ready:", store.count(), "chunks in", settings.data_dir / "chroma")
    return store.count()


def main():
    parser = argparse.ArgumentParser(description="Build local NetGuard RAG index")
    parser.add_argument("--download-mitre", action="store_true", help="Fetch official pinned MITRE ATT&CK v20.0 JSON; can be large")
    parser.add_argument("--mitre-file", type=Path, help="Ingest a previously downloaded Enterprise ATT&CK STIX file")
    parser.add_argument("--docs-dir", type=Path, help="Local directory of trusted PDF/MD/TXT documents")
    args = parser.parse_args()
    if args.mitre_file and args.download_mitre:
        parser.error("Choose either --mitre-file or --download-mitre")
    build_index(args.mitre_file, args.docs_dir, args.download_mitre)


if __name__ == "__main__":
    main()
