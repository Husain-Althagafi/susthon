import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .llm_client import LLMClientError, generate_reply
from .pipeline import run_pipeline
from .prompts import build_prompt
from .storage import get_analysis, save_analysis

app = FastAPI(title="Scope 3 Chat Integration")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/analyze_invoice")
async def analyze_invoice(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    suffix = Path(file.filename).suffix or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    analysis = run_pipeline(str(tmp_path))
    save_analysis(analysis["invoice_id"], analysis)
    print(f"[analyze_invoice] invoice_id={analysis['invoice_id']}")
    return {"invoice_id": analysis["invoice_id"], "analysis": analysis}


@app.post("/chat")
async def chat(body: dict):
    invoice_id = body.get("invoice_id")
    message = body.get("message")

    if not invoice_id:
        raise HTTPException(status_code=400, detail="invoice_id is required.")
    if not message or not message.strip():
        raise HTTPException(status_code=400, detail="message is required.")

    analysis = get_analysis(invoice_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Unknown invoice_id")

    prompt = build_prompt(message, analysis)
    try:
        reply = generate_reply(prompt)
    except LLMClientError as exc:
        return JSONResponse(status_code=503, content={"error": str(exc)})

    print(f"[chat] invoice_id={invoice_id} message_len={len(message)}")
    return {"reply": reply}


@app.get("/health")
def health():
    return {"status": "ok"}
