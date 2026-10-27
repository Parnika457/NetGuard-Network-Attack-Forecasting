"""Semantic retrieval plus light lexical and attack-label relevance scoring."""
import re
from .schemas import Source

STOP = set("the a an and or of to for with from in on is are at by will can how what why when that this my our i you attack predicted probability model next network risk explain suggest within".split())


def tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z][a-z0-9_-]{2,}", text.lower()) if w not in STOP}


class Retriever:
    def __init__(self, store, embeddings):
        self.store = store
        self.embeddings = embeddings

    def retrieve(self, query: str, *, attack_class: str | None = None, top_k=6, general_only=False) -> list[Source]:
        qvec = self.embeddings.encode([query])[0]
        # A broad search provides citations beyond the generic label guide;
        # a filtered search ensures relevant class guides can be considered.
        candidates = self.store.query(qvec, max(18, top_k * 5))
        if attack_class and attack_class != "Normal":
            candidates += self.store.query(qvec, min(6, top_k * 2), attack_class=attack_class)
        dedup = {c["id"]: c for c in candidates}
        qt = tokens(query)
        scored = []
        for c in dedup.values():
            meta = c["metadata"]
            if general_only and meta.get("attack_class") not in ("general", None, ""):
                continue
            similarity = max(0.0, min(1.0, 1.0 - float(c["distance"])))
            lexical = len(qt & tokens(c["text"])) / max(1, len(qt))
            matched = bool(attack_class and meta.get("attack_class") == attack_class)
            score = .72 * similarity + .18 * lexical + (.10 if matched else 0)
            scored.append((score, similarity, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        selected, per_doc = [], {}
        for score, sim, c in scored:
            doc_id = c["metadata"].get("doc_id", c["id"])
            if per_doc.get(doc_id, 0) >= 2:
                continue
            per_doc[doc_id] = per_doc.get(doc_id, 0) + 1
            meta = c["metadata"]
            selected.append(Source(
                source_id=f"S{len(selected) + 1}", title=meta["title"],
                source_type=meta["source_type"], source_url=meta.get("source_url") or None,
                location=meta.get("location", ""),
                attack_class=meta.get("attack_class") if meta.get("attack_class") != "general" else None,
                similarity=round(sim, 4), excerpt=c["text"][:1350],
            ))
            if len(selected) >= top_k:
                break
        return selected
