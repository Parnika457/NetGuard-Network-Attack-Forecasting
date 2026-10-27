"""Run from rag/: uvicorn app.main:app --reload"""
from functools import lru_cache
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .schemas import AnalyzeRequest, AnalyzeResponse, RetrieveRequest, RetrieveResponse
from .service import RagService

settings = get_settings()
app = FastAPI(title="NetGuard RAG", description="Evidence-grounded analyst explanations of separate ML predictions", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@lru_cache(maxsize=1)
def service() -> RagService:
    return RagService(get_settings())


@app.get("/health")
def health():
    return {"status": "ok", "service": "netguard-rag"}


@app.get("/api/rag/status")
def status(rag: RagService = Depends(service)):
    return {
        "indexed_chunks": rag.store.count(),
        "embedding_model": rag.settings.embedding_model,
        "llm_configured": bool(rag.settings.gemini_api_key),
    }


@app.post("/api/rag/retrieve", response_model=RetrieveResponse)
def retrieve(req: RetrieveRequest, rag: RagService = Depends(service)):
    if not rag.store.count():
        raise HTTPException(503, "Knowledge index empty. Run: python -m app.ingest")
    try:
        return rag.retrieve(req)
    except Exception as exc:
        raise HTTPException(500, f"Retrieval failed: {type(exc).__name__}") from exc


@app.post("/api/rag/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest, rag: RagService = Depends(service)):
    if not rag.store.count():
        raise HTTPException(503, "Knowledge index empty. Run: python -m app.ingest")
    if not rag.settings.gemini_api_key:
        raise HTTPException(503, "GEMINI_API_KEY missing. See rag/.env.example")
    try:
        return rag.analyze(req)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        # Do not expose credentials, LLM details, context or internal traces in an API response.
        raise HTTPException(502, f"RAG analysis failed ({type(exc).__name__}); check server logs") from exc
