"""Local, reproducible settings for the VS Code standalone RAG service."""
from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path
from dotenv import load_dotenv

RAG_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(RAG_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    knowledge_dir: Path
    embedding_model: str
    chroma_collection: str
    gemini_model: str
    gemini_api_key: str
    cors_origins: tuple[str, ...]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        data_dir=Path(os.getenv("RAG_DATA_DIR") or (RAG_ROOT / "data")).expanduser().resolve(),
        knowledge_dir=Path(os.getenv("RAG_KNOWLEDGE_DIR") or (RAG_ROOT / "knowledge")).expanduser().resolve(),
        embedding_model=os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        chroma_collection=os.getenv("CHROMA_COLLECTION", "netguard_knowledge_v1"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        cors_origins=tuple(x.strip() for x in os.getenv(
            "RAG_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",") if x.strip()),
    )
