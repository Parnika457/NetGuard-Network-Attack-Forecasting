"""App-level orchestration. Swap in actual model outputs at this boundary."""
from .config import Settings
from .embeddings import Embeddings
from .retriever import Retriever
from .schemas import AnalyzeRequest, AnalyzeResponse, RetrieveRequest, RetrieveResponse
from .store import VectorStore
from .llm import generate_analysis


class RagService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.store = VectorStore(settings.data_dir, settings.chroma_collection, settings.embedding_model)
        self.retriever = Retriever(self.store, Embeddings(settings.embedding_model))

    def retrieve(self, request: RetrieveRequest) -> RetrieveResponse:
        sources = self.retriever.retrieve(request.query, attack_class=request.attack_class, top_k=request.top_k)
        return RetrieveResponse(results=sources, count=len(sources))

    def analyze(self, request: AnalyzeRequest) -> AnalyzeResponse:
        parts = [request.question]
        target_class = None
        if request.detection:
            target_class = request.detection.attack_class
            parts.append(f"Present detected UNSW-NB15 class: {target_class}")
        if request.forecast:
            f = request.forecast
            parts.append(f"Forecast: {f.target} over {f.horizon_minutes} minutes")
            if f.target == "specific_attack":
                parts.append(f"Future class: {f.attack_class}")
                target_class = target_class or f.attack_class
        sources = self.retriever.retrieve(". ".join(parts), attack_class=target_class, top_k=request.top_k)
        if not sources:
            raise ValueError("RAG index is empty or retrieval returned no evidence. Run ingestion first.")
        answer = generate_analysis(request, sources, api_key=self.settings.gemini_api_key, model=self.settings.gemini_model)
        warnings = ["RAG explains model outputs; it does not make or validate ML predictions."]
        if request.forecast and request.forecast.target == "any_attack":
            warnings.append("The forecast concerns ANY attack within the horizon; it does not identify a future attack class.")
        if request.detection or request.forecast:
            warnings.append("Model confidence/probability may not be calibrated; consult held-out evaluation before interpreting absolute risk.")
        if not answer.cited_source_ids:
            warnings.append("The generated answer cites no retrieved sources; verify factual claims independently.")
        return AnalyzeResponse(
            summary=answer.summary, explanation=answer.explanation,
            investigation_steps=answer.investigation_steps, limitations=answer.limitations,
            cited_source_ids=answer.cited_source_ids, sources=sources,
            warnings=warnings, model_name=self.settings.gemini_model,
        )
