import io
import uuid
from pathlib import Path
from typing import Dict

from .aggregate import build_analysis
from .emissions import compute_emissions
from .factors import load_factors
from .ocr import extract_text
from .parser import parse_invoice_text


def run_pipeline(file_path: str) -> Dict:
    """
    Run OCR, parse, categorize, calculate emissions, and return standardized analysis JSON.
    """
    path = Path(file_path)
    invoice_id = f"INV-{uuid.uuid4()}"

    content = path.read_bytes()
    text = extract_text(io.BytesIO(content), filename=path.name)

    factors = load_factors()
    items = [compute_emissions(item, factors) for item in parse_invoice_text(text)]

    analysis = build_analysis(invoice_id, items)
    return analysis
