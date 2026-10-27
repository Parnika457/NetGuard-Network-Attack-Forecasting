from app.chunking import Document, split_document


def test_chunks_preserve_metadata_and_overlap():
    d = Document("Test", " ".join(str(i) for i in range(22)), "local", None, "file", "DoS")
    chunks = split_document(d, max_words=10, overlap_words=3)
    assert len(chunks) == 3
    assert all(c.metadata["attack_class"] == "DoS" for c in chunks)
    assert "7 8 9" in chunks[1].text
    assert chunks[0].id != chunks[1].id


def test_whitespace_only_empty():
    assert split_document(Document("a", " \n ", "local", None, "x")) == []
