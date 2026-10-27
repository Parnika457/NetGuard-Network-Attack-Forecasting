"""One shared embedding model for ingestion and queries."""
from functools import lru_cache


@lru_cache(maxsize=2)
def load_model(name: str):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(name)


class Embeddings:
    def __init__(self, name: str):
        self.name = name

    def encode(self, texts: list[str]) -> list[list[float]]:
        vectors = load_model(self.name).encode(
            texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False
        )
        return vectors.tolist()
