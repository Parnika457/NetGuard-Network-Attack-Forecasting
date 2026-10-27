import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT / 'rag'))
from app.schemas import AnalyzeRequest
from app.chunking import split_document
from app.knowledge import reference_summary_documents
from app.retriever import Retriever
import rag_bridge


def _forecast_record():
    return {'id': 39, 'event_type': 'FORECAST_INFERENCE', 'prediction': {
        'forecast': {'h5': 0.0000001, 'h10': 0.00072, 'h15': 0.026},
        'family_eta': {'family_if_onset': 'BRUTE_AUTH', 'family_probability_if_onset': 0.70,
                       'conditional_eta_minutes': 14.0, 'p_onset_within_15': 0.21},
        'telemetry': {'data_kind': 'simulated_one_minute_flow_aggregates',
                      'summary': {'packets_per_second': 225.4, 'throughput_kib_per_second': 89.3,
                                  'flows_per_minute': 1237, 'packets_per_minute': 13525}},
    }}


def test_saved_forecast_and_synthetic_features_are_kept_separate():
    payload = rag_bridge.build_analysis_request(_forecast_record())
    contract = AnalyzeRequest.model_validate(payload)
    assert contract.forecast_bundle.h10 == 0.00072
    assert contract.family_eta.family_probability_if_onset == 0.70
    assert contract.family_eta.conditional_eta_minutes == 14
    assert contract.simulated_replay_features.flows_per_minute == 1237
    assert contract.observations is None


def test_no_fake_observations_when_telemetry_missing():
    record = _forecast_record()
    del record['prediction']['telemetry']
    payload = rag_bridge.build_analysis_request(record)
    assert 'simulated_replay_features' not in payload


def test_endpoint_returns_exact_saved_values_for_frontend(monkeypatch):
    monkeypatch.setattr(rag_bridge, 'get_event', lambda n: _forecast_record())
    monkeypatch.setattr(rag_bridge, '_rag_post', lambda body: {'summary': 'Test response'})
    api = FastAPI()
    api.include_router(rag_bridge.router)
    response = TestClient(api).post('/api/rag/explain/history/39')
    assert response.status_code == 200
    context = response.json()['prediction_context']
    assert context == {'kind': 'forecast', 'h5': 0.0000001, 'h10': 0.00072, 'h15': 0.026,
                       'family_if_onset': 'BRUTE_AUTH', 'family_probability_if_onset': 0.70,
                       'conditional_eta_minutes': 14.0}


def test_curated_summaries_have_verified_links_and_family_metadata():
    docs = list(reference_summary_documents(ROOT / 'rag/knowledge'))
    assert len(docs) >= 8
    official = [doc for doc in docs if doc.source_url]
    assert all(doc.source_url.startswith(('https://csrc.nist.gov/', 'https://attack.mitre.org/')) for doc in official)
    brute = next(doc for doc in docs if doc.future_family == 'BRUTE_AUTH')
    assert 'research summary' in brute.title.lower()
    chunk = split_document(brute)[0]
    assert chunk.metadata['future_family'] == 'BRUTE_AUTH'
    assert chunk.metadata['source_url'] == 'https://attack.mitre.org/techniques/T1110/'


class DummyEmbedding:
    def encode(self, texts):
        return [[0.1, 0.2]]


class DummyStore:
    def query(self, vector, top_k, attack_class=None):
        entries = []
        for i, (family, title, url) in enumerate([
            ('', 'NetGuard forecasting guidance', ''),
            ('', 'NIST Incident Response', 'https://csrc.nist.gov/pubs/sp/800/61/r3/final'),
            ('BRUTE_AUTH', 'Brute force', 'https://attack.mitre.org/techniques/T1110/'),
            ('DOS_DDOS', 'Network denial of service', 'https://attack.mitre.org/techniques/T1498/'),
            ('', 'Unrelated current DoS class guide', ''),
        ]):
            attack = 'DoS' if i == 4 else 'general'
            entries.append({'id': str(i), 'text': title + ' recommended investigation checks',
                            'distance': 0.2, 'metadata': {'title': title, 'source_type': 'curated_reference_summary',
                                                         'source_url': url, 'attack_class': attack,
                                                         'future_family': family, 'doc_id': str(i),
                                                         'location': 'netguard_forecasting_guidance.md' if i == 0 else 'references'}})
        return [x for x in entries if attack_class is None or x['metadata']['attack_class'] == attack_class]


def test_future_family_filter_and_unique_citations():
    retriever = Retriever(DummyStore(), DummyEmbedding())
    brute = retriever.retrieve('forecast next family authentication investigation', top_k=5,
                               general_only=True, future_family='BRUTE_AUTH')
    titles = [source.title for source in brute]
    assert titles[0] == 'Brute force'
    assert 'NIST Incident Response' in titles
    assert 'Network denial of service' not in titles
    assert 'Unrelated current DoS class guide' not in titles
    assert len(titles) == len(set(titles))
    dos = retriever.retrieve('forecast conditional denial of service', top_k=5,
                             general_only=True, future_family='DOS_DDOS')
    assert dos[0].title == 'Network denial of service'
    assert 'Brute force' not in [source.title for source in dos]


def test_no_conditional_family_retrieval_for_any_attack_forecast():
    sources = Retriever(DummyStore(), DummyEmbedding()).retrieve(
        'forecast H10 any attack', top_k=5, general_only=True)
    assert all('Brute force' != s.title and 'Network denial of service' != s.title for s in sources)
