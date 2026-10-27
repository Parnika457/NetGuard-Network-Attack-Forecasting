"""Persistent Chroma collection with explicit vectors (no implicit Chroma embedding model)."""
import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .chunking import Chunk


class VectorStore:
    def __init__(self, data_dir: Path, collection_name: str, embedding_model: str, *, allow_rebuild: bool = False):
        import chromadb
        self.data_dir = data_dir
        self.embedding_model = embedding_model
        self.manifest_file = data_dir / "index_manifest.json"
        data_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=str(data_dir / "chroma"),
            settings=chromadb.Settings(anonymized_telemetry=False),
        )
        self.collection_name = collection_name
        if self.manifest_file.exists():
            manifest = json.loads(self.manifest_file.read_text(encoding="utf-8"))
            if manifest.get("embedding_model") != embedding_model and not allow_rebuild:
                raise RuntimeError(
                    f"Index was built with {manifest.get('embedding_model')}; currently configured "
                    f"for {embedding_model}. Rebuild the index before serving requests."
                )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=None,
            configuration={"hnsw": {"space": "cosine"}},
        )

    def reset(self):
        try:
            self.client.delete_collection(self.collection_name)
        except ValueError:
            pass
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=None,
            configuration={"hnsw": {"space": "cosine"}},
        )

    def upsert(self, chunks: list["Chunk"], vectors: list[list[float]], batch_size=100):
        for offset in range(0, len(chunks), batch_size):
            part = chunks[offset:offset + batch_size]
            vec = vectors[offset:offset + batch_size]
            self.collection.upsert(
                ids=[x.id for x in part],
                documents=[x.text for x in part],
                metadatas=[x.metadata for x in part],
                embeddings=vec,
            )

    def query(self, vector: list[float], top_k: int, attack_class: str | None = None) -> list[dict]:
        if self.count() == 0:
            return []
        args = {
            "query_embeddings": [vector],
            "n_results": min(top_k, self.count()),
            "include": ["documents", "metadatas", "distances"],
        }
        if attack_class is not None:
            args["where"] = {"attack_class": attack_class}
        try:
            data = self.collection.query(**args)
        except Exception as exc:
            # Chroma may reject filtered queries when no matching metadata exists.
            if attack_class is not None and "results" in str(exc).lower():
                return []
            raise
        return [
            {"id": id_, "text": doc, "metadata": meta, "distance": dist}
            for id_, doc, meta, dist in zip(
                data["ids"][0], data["documents"][0], data["metadatas"][0], data["distances"][0]
            )
        ]

    def count(self) -> int:
        return self.collection.count()

    def write_manifest(self, chunks: int):
        self.manifest_file.write_text(json.dumps({
            "embedding_model": self.embedding_model,
            "collection_name": self.collection_name,
            "chunks": chunks,
        }, indent=2), encoding="utf-8")
