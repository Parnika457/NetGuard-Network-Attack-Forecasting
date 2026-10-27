"""Offline retrieval quality smoke evaluation (NOT intrusion-detection model metrics)."""
import json
from .config import get_settings
from .service import RagService


def main():
    settings = get_settings()
    cases = json.loads((settings.knowledge_dir / "retrieval_eval.json").read_text(encoding="utf-8"))
    rag = RagService(settings)
    if not rag.store.count():
        raise SystemExit("Index not built. Run python -m app.ingest first.")
    hits, rr = 0, 0.0
    for case in cases:
        sources = rag.retriever.retrieve(case["query"], attack_class=case["attack_class"], top_k=5)
        rank = next((i for i, s in enumerate(sources, 1) if s.title == case["expected_title"]), None)
        hits += bool(rank)
        rr += 1/rank if rank else 0.0
        print(f"{'PASS' if rank else 'MISS'} | rank={rank or '-'} | {case['expected_title']}")
    print(f"Recall@5: {hits}/{len(cases)} ({hits/len(cases):.1%})")
    print(f"MRR@5: {rr/len(cases):.3f}")
    print("These numbers test retrieval of chosen guides, not attack detection, calibration, or LLM factuality.")


if __name__ == "__main__":
    main()
