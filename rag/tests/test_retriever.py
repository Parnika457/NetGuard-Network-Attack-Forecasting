from app.retriever import Retriever


class FakeEmbedding:
    def encode(self, texts):
        return [[0.1, 0.2]]


class FakeStore:
    def query(self, vector, top_k, attack_class=None):
        entries = [
            {"id": "1", "text": "DoS DoS flooding and excessive requests", "distance": 0.1,
             "metadata": {"title": "DoS guide", "source_type": "project_guide", "source_url": "", "location": "seed", "attack_class": "DoS", "doc_id": "a"}},
            {"id": "2", "text": "Reconnaissance port scan of network services", "distance": 0.2,
             "metadata": {"title": "Scan guide", "source_type": "project_guide", "source_url": "", "location": "seed", "attack_class": "Reconnaissance", "doc_id": "b"}},
        ]
        return [x for x in entries if not attack_class or x["metadata"]["attack_class"] == attack_class]


def test_attack_class_guide_priority_and_citations():
    output = Retriever(FakeStore(), FakeEmbedding()).retrieve("Explain DoS flooding", attack_class="DoS", top_k=2)
    assert output[0].title == "DoS guide"
    assert [s.source_id for s in output] == ["S1", "S2"]
