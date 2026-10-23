# TechTaru Digital - Generative AI Engineer Assignment

**Candidate:** Raghav Goyal  
**Email:** raghavgoyal6046@gmail.com  

Repository containing solutions for the technical assessment tasks:
1. **Task 1: PDF RAG Pipeline** - Interactive PDF chat application with vector retrieval and source grounding.
2. **Task 2: Data Extraction Bot** - REST API for structured extraction from unstructured text (resumes and invoices) with Pydantic validation.

---

## Project Structure

```
.
├── task-1-rag-pdf-chatbot/           # Task 1: RAG Pipeline
│   ├── app.py                        # Streamlit UI
│   ├── rag_engine.py                 # Ingestion, chunking, ChromaDB indexing, retrieval
│   ├── vector_math.py                # Vector similarity comparison (Cosine vs Euclidean)
│   ├── rag_config.py                 # Configuration and environment setup
│   ├── sample_docs/                  # Sample test documents
│   └── tests/
│       └── test_rag.py               # Unit & integration tests
│
├── task-2-data-extraction-bot/       # Task 2: Data Extraction Microservice
│   ├── main.py                       # FastAPI application & routes
│   ├── web_ui.py                     # Interactive test dashboard (/app)
│   ├── schemas.py                    # Pydantic v2 schemas for Resume & Invoice
│   ├── extractor.py                  # Extraction engine with validation logic
│   ├── extractor_config.py           # Configuration and model settings
│   ├── sample_inputs/                # Sample test inputs
│   └── tests/
│       └── test_api.py               # API & validation test suite
│
├── requirements.txt                  # Top-level dependencies reference
└── README.md
```

---

## Setup Instructions

### 1. Environment & Dependencies

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies for both tasks:

```bash
pip install -r task-1-rag-pdf-chatbot/requirements.txt
pip install -r task-2-data-extraction-bot/requirements.txt
```

### 2. API Key Configuration

Both tasks use Google Gemini (`gemini-3.5-flash`). Both also include an offline mock/heuristic mode so they can be run and tested without an API key if needed.

Create `.env` files from the provided examples:

```bash
cp task-1-rag-pdf-chatbot/.env.example task-1-rag-pdf-chatbot/.env
cp task-2-data-extraction-bot/.env.example task-2-data-extraction-bot/.env
```

Add your Gemini API key in both `.env` files:
```env
GEMINI_API_KEY=your_gemini_api_key
```

---

## Running the Applications

### Task 1: PDF RAG Chatbot (Streamlit)

```bash
cd task-1-rag-pdf-chatbot
streamlit run app.py
```

- App runs at: `http://localhost:8501`
- Upload any PDF or click "Load Prebuilt Sample PDF" from the sidebar to test.
- Includes a dedicated tab demonstrating Cosine Similarity vs. Euclidean Distance.

### Task 2: Data Extraction Bot (FastAPI)

```bash
cd task-2-data-extraction-bot
uvicorn main:app --reload --port 8000
```

- Web Dashboard: `http://localhost:8000/app`
- Swagger UI (OpenAPI): `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

---

## Running Tests

All unit, integration, and edge-case tests can be run using pytest:

```bash
# Run all tests
pytest -v

# Or run per-task
pytest task-1-rag-pdf-chatbot/tests/test_rag.py -v
pytest task-2-data-extraction-bot/tests/test_api.py -v
```

---

## Implementation Notes

- **Task 1 (RAG Pipeline):**
  - Text extraction uses `pypdf`, preserving page numbers across chunks for source attribution.
  - Chunking uses `RecursiveCharacterTextSplitter` with 1000-character chunks and 200-character overlap.
  - Chunks are indexed in ChromaDB using cosine distance (`hnsw:space = "cosine"`).
  - Out-of-scope queries are filtered by a cosine distance threshold (> 0.82) to prevent hallucinations, returning a clean fallback message without unnecessary model calls.
  - Resetting or uploading a new PDF purges existing chunks to prevent cross-document contamination.

- **Task 2 (Data Extraction):**
  - Uses Pydantic v2 schemas (`ResumeData`, `InvoiceData`) with regex field validators for data sanitization.
  - Untrusted input text is wrapped in `<document_text>` XML tags with prompt guardrails to resist prompt injection attempts.
  - Missing fields evaluate to `null` or empty lists rather than assumed or generated values.
  - Built-in business checks detect invoice arithmetic mismatches (subtotal + tax vs. total) as non-blocking warnings.
