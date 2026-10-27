"""Orchestrate evidence retrieval and generated analysis of saved model outputs."""
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
            parts.append(f"Present-traffic classification: {target_class}")
        if request.forecast:
            forecast = request.forecast
            parts.append(f"Future prediction {forecast.target} over {forecast.horizon_minutes} minutes")
            if forecast.target == "specific_attack":
                target_class = target_class or forecast.attack_class
        if request.forecast_bundle:
            forecast = request.forecast_bundle
            parts.append("Any-attack onset H5 H10 H15 forecast, model interpretation, response and independent investigation")
            future_family = request.family_eta.family_if_onset if request.family_eta else None
            if future_family:
                parts.append(f"Conditional future family {future_family}; investigative log evidence and verification")
            sources = self.retriever.retrieve(
                ". ".join(parts), top_k=request.top_k, general_only=True, future_family=future_family,
            )
        else:
            sources = self.retriever.retrieve(". ".join(parts), attack_class=target_class,
                                              top_k=request.top_k)
        if not sources:
            raise ValueError("RAG index is empty or retrieval returned no evidence. Run ingestion first.")
        answer = generate_analysis(request, sources, api_key=self.settings.gemini_api_key,
                                   model=self.settings.gemini_model)
        # Short, distinct caveats available to API clients. The frontend displays
        # the assessment instead of repeating these caveats in multiple sections.
        warnings = ["Analysis is based on a separate ML prediction, not a confirmed incident."]
        if request.family_eta:
            warnings.append("Family and ETA are conditional estimates from a separate model.")
        if not answer.cited_source_ids:
            warnings.append("No retrieved source was cited; verify factual claims independently.")
        return AnalyzeResponse(
            summary=answer.summary, explanation=answer.explanation,
            investigation_steps=answer.investigation_steps, limitations=answer.limitations,
            cited_source_ids=answer.cited_source_ids, sources=sources,
            warnings=warnings, model_name=self.settings.gemini_model,
        )
