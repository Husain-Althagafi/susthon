import json
import os
from typing import Any, Dict, List, Optional

import requests

API_KEY = os.getenv("GEMINI_API_KEY")
# Use a model that supports generateContent on v1beta; override via GEMINI_MODEL_NAME if needed.
MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
API_URL = os.getenv(
    "GEMINI_API_URL",
    f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent",
)


class LLMClientError(Exception):
    pass


class LLMNoItemsError(LLMClientError):
    """Raised when the LLM succeeds but returns no usable items."""


def _post_to_llm(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not API_KEY:
        raise LLMClientError("Missing GEMINI_API_KEY environment variable.")

    try:
        response = requests.post(
            f"{API_URL}?key={API_KEY}",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        if not response.ok:
            try:
                detail = response.json().get("error", {}).get("message", "")
            except Exception:
                detail = response.text
            raise LLMClientError(f"LLM request failed ({response.status_code}): {detail}")
        return response.json()
    except LLMClientError:
        raise
    except Exception as exc:
        raise LLMClientError(f"LLM request failed: {exc}") from exc


def _extract_text_from_candidates(data: Dict[str, Any]) -> str:
    candidates = data.get("candidates") or []
    if not candidates:
        raise LLMClientError("No candidates returned from Gemini.")
    text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    if not text:
        raise LLMClientError("Empty response from Gemini.")
    return text.strip()


def generate_reply(prompt: str) -> str:
    payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    data = _post_to_llm(payload)
    return _extract_text_from_candidates(data)


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return None
            value = stripped.replace(",", "").replace("$", "")
        return float(value)
    except Exception:
        return None


def _normalize_item(entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(entry, dict):
        return None
    supplier = str(entry.get("supplier") or "Unknown Supplier").strip() or "Unknown Supplier"
    description = str(entry.get("description") or "Unknown item").strip() or "Unknown item"

    normalized: Dict[str, Any] = {"supplier": supplier, "description": description}
    for key in ("amount_usd", "qty_kg", "weight_tons", "distance_km"):
        num = _to_float(entry.get(key))
        if num is not None:
            normalized[key] = num

    category = entry.get("category")
    if category:
        normalized["category"] = str(category)

    return normalized


def extract_invoice_items(invoice_text: str) -> List[Dict]:
    """
    Use the LLM to extract structured invoice items from raw OCR text.
    Returns a list of dicts with numeric fields normalized for downstream emissions logic.
    """
    prompt = (
        "Extract structured invoice line items from the raw text below.\n"
        "Return only JSON with an 'items' array. Each item must include:\n"
        "- supplier (string)\n"
        "- description (string)\n"
        "- amount_usd (number or null)\n"
        "- qty_kg (number or null, kilograms)\n"
        "- weight_tons (number or null, metric tons)\n"
        "- distance_km (number or null, kilometers for transport legs)\n"
        "- category (steel, transport, packaging, other if clear)\n"
        "Use numeric values only; strip currency symbols. If supplier is missing, reuse the last "
        "supplier or 'Unknown Supplier'. Do not hallucinate items not in the text. Respond with JSON only.\n\n"
        f"INVOICE TEXT:\n{invoice_text}"
    )

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }

    data = _post_to_llm(payload)
    raw_text = _extract_text_from_candidates(data)

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise LLMClientError(f"LLM returned non-JSON response: {exc}") from exc

    items_payload = parsed.get("items") if isinstance(parsed, dict) else parsed
    if not isinstance(items_payload, list):
        raise LLMClientError("LLM response missing 'items' list.")

    normalized_items = [item for item in (_normalize_item(entry) for entry in items_payload) if item]
    if not normalized_items:
        raise LLMNoItemsError("LLM did not return any usable items.")

    return normalized_items
