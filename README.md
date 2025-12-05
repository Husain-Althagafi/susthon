Scope 3 Invoice Analyzer + Chat

- Upload an invoice, extract items (LLM-first with rule fallback), estimate Scope 3 emissions, and chat about the results.
- Backend: FastAPI (`src/server.py`) plus in-memory storage.
- Frontend: Streamlit dashboard (`src/app.py`) with upload, charts, and chat.

Prereqs
- Python 3.10+ recommended.
- Tesseract installed and on PATH for OCR (for PDFs/images); plain text works without it.
- Google Gemini key in env var `GEMINI_API_KEY` (LLM extraction + chat).

Setup
- Create venv and install deps:
  - `python -m venv .venv && .\.venv\Scripts\activate`
  - `pip install -r requirements.txt`
- Env vars (defaults shown):
  - `GEMINI_API_KEY` (required)
  - `GEMINI_MODEL_NAME=gemini-2.5-flash`
  - `GEMINI_API_URL=https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL_NAME}:generateContent`

Run options
- Streamlit UI (upload, charts, chat): `streamlit run src/app.py`
- API server: `uvicorn src.server:app --reload`
  - Analyze: `POST /analyze_invoice` (multipart `file`)
  - Chat: `POST /chat` with JSON `{"invoice_id": "...", "message": "..." }`
- Health: `GET /health`

How the pipeline works
- OCR: `src/ocr.py` reads PDF/image/text.
- Parsing: `src/parser.py` calls Gemini (`extract_invoice_items`) to get structured lines; falls back to rules if LLM fails.
- Categorize + emissions: `src/emissions.py`, `src/categorize.py`, factors in `data/emission_factors.json`.
- Aggregation + summary JSON: `src/aggregate.py`, orchestrated by `src/pipeline.py::run_pipeline`.

Sample data
- `data/sample_invoices/invoice1.txt` can be used via the Streamlit "Use sample invoice" button.

Troubleshooting
- Missing key → set `GEMINI_API_KEY`.
- OCR errors on Windows → ensure Tesseract is installed and `tesseract.exe` is on PATH.
- LLM returns non-JSON → parser logs a fallback message and uses heuristic extraction instead.
