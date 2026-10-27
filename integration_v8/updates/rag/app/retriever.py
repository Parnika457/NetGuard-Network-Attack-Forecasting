"""Sentence-embedding retrieval with topic-aware ranking and one citation per document."""
import re
from .schemas import Source

STOP = set("the a an and or of to for with from in on is are at by will can how what why when that this my our i you attack predicted probability model next network risk explain suggest within".split())


def tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z][a-z0-9_-]{2,}", text.lower()) if w not in STOP}


class Retriever:
    def __init__(self, store, embeddings):
        self.store = store
        self.embeddings = embeddings

    def retrieve(self, query: str, *, attack_class: str | None = None, top_k=6,
                 general_only=False, future_family: str | None = None) -> list[Source]:
        qvec = self.embeddings.encode([query])[0]
        # Large enough to include curated guidance in the small default index.
        candidates = self.store.query(qvec, max(64, top_k * 12))
        if attack_class and attack_class != "Normal":
            candidates += self.store.query(qvec, min(6, top_k * 2), attack_class=attack_class)
        dedup = {c["id"]: c for c in candidates}
        qt = tokens(query)
        scored = []
        for c in dedup.values():
            meta = c["metadata"]
            family = meta.get("future_family") or ""
            if general_only:
                if meta.get("attack_class") not in ("general", None, ""):
                    continue
                if family and family != future_family:
                    continue
            similarity = max(0.0, min(1.0, 1.0 - float(c["distance"])))
            lexical = len(qt & tokens(c["text"])) / max(1, len(qt))
            matched_detection = bool(attack_class and meta.get("attack_class") == attack_class)
            matched_future = bool(future_family and family == future_family)
            official = meta.get("source_type") == "curated_reference_summary"
            score = (.66 * similarity + .16 * lexical + (.10 if matched_detection else 0)
                     + (.28 if matched_future else 0) + (.05 if official else 0))
            scored.append((score, similarity, c))
        scored.sort(key=lambda x: x[0], reverse=True)

        # When a future family is supplied, reliably provide a relevant published
        # technique summary, the NIST incident-response reference and the model
        # contract, rather than several excerpts from one project document.
        ordered = []
        used = set()
        if general_only:
            preferred = [
                lambda m: bool(future_family and m.get("future_family") == future_family
                               and m.get("source_url")),
                lambda m: "csrc.nist.gov/pubs/sp/800/61" in m.get("source_url", ""),
                lambda m: "netguard_forecasting_guidance" in m.get("location", ""),
            ]
            for selector in preferred:
                for score, sim, c in scored:
                    if selector(c["metadata"]):
                        doc_id = c["metadata"].get("doc_id", c["id"])
                        if doc_id not in used:
                            ordered.append((score, sim, c)); used.add(doc_id)
                        break
        for score, sim, c in scored:
            doc_id = c["metadata"].get("doc_id", c["id"])
            if doc_id in used:
                continue
            ordered.append((score, sim, c)); used.add(doc_id)

        # Prefer unique documents over repeated overlapping chunks; IDs reflect
        # the final order that is passed to Gemini.
        selected = []
        for score, similarity, c in ordered[:top_k]:
            meta = c["metadata"]
            selected.append(Source(
                source_id=f"S{len(selected) + 1}", title=meta["title"],
                source_type=meta["source_type"], source_url=meta.get("source_url") or None,
                location=meta.get("location", ""),
                attack_class=meta.get("attack_class") if meta.get("attack_class") != "general" else None,
                similarity=round(similarity, 4), excerpt=c["text"][:1350],
            ))
        return selected
