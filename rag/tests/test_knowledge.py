from pathlib import Path
from app.knowledge import seed_documents, mitre_documents
from app.config import RAG_ROOT


def test_all_ten_classes_present():
    classes = {d.attack_class for d in seed_documents(RAG_ROOT / "knowledge")}
    assert classes == {"Analysis","Backdoor","DoS","Exploits","Fuzzers","Generic","Normal","Reconnaissance","Shellcode","Worms"}


def test_official_mitre_stix_parser(tmp_path: Path):
    p = tmp_path / "test.json"
    p.write_text('''{"objects":[
      {"type":"attack-pattern","name":"Example","description":"A valid description for a defensive test technique and supporting context beyond fifty characters.","external_references":[{"source_name":"mitre-attack","external_id":"T1234","url":"https://attack.mitre.org/techniques/T1234/"}]},
      {"type":"attack-pattern","revoked":true,"name":"Revoked","description":"Do not use this valid description for revoked technique source entries.","external_references":[{"source_name":"mitre-attack","external_id":"T9999"}]}
    ]}''')
    docs = list(mitre_documents(p))
    assert len(docs) == 1
    assert docs[0].source_url == "https://attack.mitre.org/techniques/T1234/"
