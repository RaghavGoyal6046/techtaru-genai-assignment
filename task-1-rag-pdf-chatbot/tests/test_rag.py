
import sys
from pathlib import Path
import pytest
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io

# Ensure parent directory is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag_engine import RAGEngine, PDFExtractionError, ScannedPDFError
from vector_math import (
    cosine_similarity,
    cosine_distance,
    euclidean_distance,
    normalize_vector,
    dot_product
)


@pytest.fixture
def sample_pdf_bytes():
    """Generates an in-memory 2-page test PDF."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawString(100, 700, "TechTaru Digital Artificial Intelligence Research Team.")
    c.drawString(100, 650, "The secret company project code name is Project Falcon.")
    c.showPage()
    c.drawString(100, 700, "Leave policy allows 24 days paid vacation annually.")
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()


@pytest.fixture
def empty_pdf_bytes():
    """Generates an in-memory PDF with blank pages (no digital text)."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()


def test_empty_file_error():
    """Empty 0-byte file should trigger PDFExtractionError."""
    engine = RAGEngine(provider="mock")
    with pytest.raises(PDFExtractionError, match="empty"):
        engine.extract_text_from_pdf(b"", "empty.pdf")


def test_corrupt_pdf_error():
    """Corrupted binary data should cleanly raise PDFExtractionError, not crash."""
    engine = RAGEngine(provider="mock")
    with pytest.raises(PDFExtractionError):
        engine.extract_text_from_pdf(b"%PDF-1.4 corrupt random bytes", "corrupt.pdf")


def test_scanned_unreadable_pdf_error(empty_pdf_bytes):
    """PDF with no extractable text should raise ScannedPDFError requesting OCR."""
    engine = RAGEngine(provider="mock")
    with pytest.raises(ScannedPDFError, match="OCR"):
        engine.extract_text_from_pdf(empty_pdf_bytes, "scanned.pdf")


def test_chunking_and_metadata(sample_pdf_bytes):
    """Verify chunks preserve page numbers and metadata."""
    engine = RAGEngine(provider="mock")
    pages = engine.extract_text_from_pdf(sample_pdf_bytes, "test.pdf")
    assert len(pages) == 2
    assert pages[0]["page"] == 1
    assert "Falcon" in pages[0]["text"]
    assert pages[1]["page"] == 2
    assert "vacation" in pages[1]["text"]

    chunks = engine.chunk_document(pages, "test.pdf")
    assert len(chunks) >= 2
    for chunk in chunks:
        assert "source" in chunk["metadata"]
        assert "page" in chunk["metadata"]
        assert chunk["metadata"]["page"] in [1, 2]


def test_grounded_qa_and_sources(sample_pdf_bytes):
    """Tests that answers are grounded and return source citations."""
    engine = RAGEngine(provider="mock")
    engine.index_pdf(sample_pdf_bytes, "test.pdf")

    # Positive query
    res = engine.generate_answer("What is the secret company project code name?")
    assert res["relevant_found"] is True
    assert len(res["sources"]) > 0
    assert any(s["page"] == 1 for s in res["sources"])


def test_anti_hallucination_fallback(sample_pdf_bytes):
    """Tests that out-of-scope query triggers strict fallback without hallucination."""
    engine = RAGEngine(provider="mock")
    engine.index_pdf(sample_pdf_bytes, "test.pdf")

    # Query with completely unrelated topic
    res = engine.generate_answer("How do I bake sourdough bread?")
    assert res["relevant_found"] is False
    assert res["answer"] == "I couldn't find this information in the uploaded document."
    assert res["sources"] == []


def test_empty_question_validation():
    """Tests empty question validation."""
    engine = RAGEngine(provider="mock")
    res = engine.generate_answer("   ")
    assert "valid question" in res["answer"].lower()


def test_document_switching_isolation(sample_pdf_bytes):
    """Indexing a second document should clear previous document chunks."""
    engine = RAGEngine(provider="mock")
    engine.index_pdf(sample_pdf_bytes, "first.pdf")
    assert engine.active_collection.count() >= 2

    # Second document with different content
    buf2 = io.BytesIO()
    c2 = canvas.Canvas(buf2, pagesize=letter)
    c2.drawString(100, 700, "Completely new document about astrophysics and black holes.")
    c2.showPage()
    c2.save()
    buf2.seek(0)
    second_bytes = buf2.read()

    engine.index_pdf(second_bytes, "second.pdf")
    assert engine.current_filename == "second.pdf"
    # Old chunks should not persist in new collection
    all_docs = engine.active_collection.get()["documents"]
    assert not any("Falcon" in d for d in all_docs)
    assert any("astrophysics" in d for d in all_docs)


def test_vector_math_identities():
    """Verifies mathematical properties of vector similarity metrics."""
    vec_a = [1.0, 0.0]
    vec_b = [1.0, 0.0]
    vec_c = [0.0, 1.0]

    # Identical vectors: cosine similarity = 1.0, distance = 0.0
    assert pytest.approx(cosine_similarity(vec_a, vec_b), 0.001) == 1.0
    assert pytest.approx(cosine_distance(vec_a, vec_b), 0.001) == 0.0
    assert pytest.approx(euclidean_distance(vec_a, vec_b), 0.001) == 0.0

    # Orthogonal vectors: cosine similarity = 0.0, distance = 1.0
    assert pytest.approx(cosine_similarity(vec_a, vec_c), 0.001) == 0.0
    assert pytest.approx(cosine_distance(vec_a, vec_c), 0.001) == 1.0

    # Opposite vectors
    vec_opp = [-1.0, 0.0]
    assert pytest.approx(cosine_similarity(vec_a, vec_opp), 0.001) == -1.0
    assert pytest.approx(cosine_distance(vec_a, vec_opp), 0.001) == 2.0
