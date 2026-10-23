# Task 2: Data Extraction Bot

FastAPI service that extracts structured data from unstructured resumes and invoices into validated Pydantic schemas.

## Features

- **Strict Schema Validation:** Powered by Pydantic v2 schemas (`ResumeData`, `InvoiceData`).
- **Prompt Isolation:** Untrusted document text is enclosed in `<document_text>` blocks with system instructions to prevent prompt injection overrides.
- **Factual Grounding:** Missing attributes return `null` or `[]` without fabricating data.
- **Business Logic Checks:** Non-blocking arithmetic checks flag discrepancies between subtotal, tax, and total amount.
- **Interactive UI & OpenAPI:** Includes a built-in dashboard at `/app` for visual testing, plus OpenAPI docs at `/docs`.
- **Offline Fallback:** Heuristic extraction engine runs automatically when no API key is configured.

## API Endpoints

- `GET /` - Service status and information
- `GET /app` - Interactive web dashboard
- `GET /health` - Health check and active engine status
- `GET /docs` - Swagger UI documentation
- `POST /extract` - Main extraction endpoint

### Example: Resume Extraction

**Request:**
```bash
curl -X POST http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d '{
    "document_type": "resume",
    "text": "Raghav Goyal is a Python and AI developer based in Jaipur with 3.5 years of experience. Contact: raghavgoyal6046@gmail.com. Skills: Python, FastAPI, LangChain, ChromaDB, Docker."
  }'
```

**Response (200 OK):**
```json
{
  "success": true,
  "document_type": "resume",
  "provider_used": "gemini-3.5-flash",
  "data": {
    "name": "Raghav Goyal",
    "email": "raghavgoyal6046@gmail.com",
    "phone": null,
    "location": "Jaipur",
    "skills": ["Python", "FastAPI", "LangChain", "ChromaDB", "Docker"],
    "experience_years": 3.5,
    "current_role": null,
    "education": [],
    "certifications": []
  },
  "warnings": []
}
```

### Example: Invoice Extraction

**Request:**
```bash
curl -X POST http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d '{
    "document_type": "invoice",
    "text": "Invoice #INV-2026-9041 Date: 2026-10-15. Vendor: TechTaru Digital. Client: Acme Corp. Subtotal: $4,700.00. Tax: $470.00. Total Amount: $5,170.00"
  }'
```

## Setup & Running

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Add your GEMINI_API_KEY to .env (or leave blank to use offline mode)
   ```

3. **Start the server:**
   ```bash
   uvicorn main:app --reload --port 8000
   ```

4. **Access the dashboard:**
   Open `http://localhost:8000/app` or check API docs at `http://localhost:8000/docs`.

## Testing

Run tests with pytest:
```bash
pytest tests/test_api.py -v
```

Tests cover:
- Endpoint health and root response
- Resume extraction into `ResumeData`
- Invoice extraction into `InvoiceData`
- Empty / whitespace text rejection (422)
- Unsupported document type handling (422)
- Missing field handling (null preservation)
- Email format validation
- Prompt injection defense
