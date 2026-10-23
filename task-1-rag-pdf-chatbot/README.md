# Task 1: PDF RAG Chatbot

An interactive document question-answering application built with Streamlit, LangChain, ChromaDB, and Google Gemini.

## Features

- **PDF Ingestion & Validation:** Validates file size (up to 25MB), checks for password protection, corrupt files, and detects scanned/image-only PDFs where OCR is required.
- **Chunking with Metadata:** Chunks text using `RecursiveCharacterTextSplitter` (1000 chars, 200 overlap) while tracking source file and page numbers for citations.
- **Vector Storage:** Uses ChromaDB with cosine distance metric (`hnsw:space = "cosine"`). Each uploaded document uses an isolated collection.
- **Source Citations:** Retrieved answers include references to specific pages with similarity scores.
- **Relevance Guardrail:** Out-of-scope questions that exceed the distance threshold (> 0.82) return a clean fallback response without making unnecessary LLM calls.
- **Vector Math Explainer:** Includes an interactive comparison tab and standalone script (`vector_math.py`) demonstrating Cosine Similarity vs. Euclidean Distance.
- **Offline Mock Fallback:** Supports an offline mode with deterministic token-hashing for automated unit testing (CI/CD) and fast local evaluation without external API dependencies.

## Vector Search Math: Cosine vs. Euclidean

In NLP and document retrieval, document chunk lengths naturally vary:
- **Cosine Similarity** measures the angle between vectors:
  $$\text{Cosine Similarity}(A, B) = \frac{A \cdot B}{\|A\| \|B\|}$$
  It is length-invariant. A short summary and a long document on the same topic share the same directional orientation.
- **Euclidean Distance (L2)** measures straight-line distance:
  $$\text{Euclidean Distance}(A, B) = \|A - B\|$$
  It is sensitive to vector magnitude. Longer text with repeated keywords produces larger magnitudes, artificially increasing Euclidean distance even when the semantic topic is identical.
- When embeddings are L2-normalized ($\|A\| = \|B\| = 1$), Euclidean distance and Cosine similarity produce the exact same ranking.

To run the standalone comparison:
```bash
python vector_math.py
```

## Setup & Running

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Add your GEMINI_API_KEY for live Gemini generation & semantic embeddings.
   # If left blank, the app runs in offline mock mode for test verification.
   ```

3. **Run the Streamlit app:**
   ```bash
   streamlit run app.py
   ```
   Open `http://localhost:8501` in your browser.

## Testing

Run the test suite:
```bash
pytest tests/test_rag.py -v
```

Tests cover:
- Empty and corrupt PDF handling
- Scanned (unextractable text) PDF detection
- Chunking and page metadata retention
- Grounded Q&A and citation retrieval
- Out-of-scope query fallback (anti-hallucination)
- Document switching isolation
- Vector similarity mathematical properties
