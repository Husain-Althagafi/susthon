import re
from typing import Dict, List

from .llm_client import LLMClientError, LLMNoItemsError, extract_invoice_items


def _extract_supplier(lines: List[str]) -> str:
    for line in lines:
        lower = line.lower()
        if "supplier" in lower or "vendor" in lower or "from:" in lower:
            if ":" in line:
                return line.split(":", 1)[1].strip() or "Unknown Supplier"
            return line.strip() or "Unknown Supplier"
    return "Unknown Supplier"


def _clean_amount(raw: str) -> float:
    cleaned = raw.replace(",", "")
    try:
        return float(cleaned)
    except Exception:
        return 0.0


def parse_invoice_text(text: str) -> List[Dict]:
    """
    Try to parse invoice text with the LLM first; fall back to heuristics if unavailable or failing.
    """
    try:
        items = extract_invoice_items(text)
        if items:
            return items
        return []
    except LLMNoItemsError as exc:
        # Explicitly respect the "no items found" signal; do not fall back to heuristics.
        print(f"[parse_invoice_text] LLM returned no items: {exc}")
        return []
    except LLMClientError as exc:
        print(f"[parse_invoice_text] LLM extraction failed, falling back to rules: {exc}")
    except Exception as exc:  # defensive catch-all so pipeline always continues
        print(f"[parse_invoice_text] Unexpected LLM error, falling back to rules: {exc}")

    return _parse_with_rules(text)


def _parse_with_rules(text: str) -> List[Dict]:
    """
    Lightweight rule-based parser that tries to extract items from invoice text.
    Each detected line with quantities or monetary amounts becomes an item.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    supplier = _extract_supplier(lines)
    current_supplier = supplier
    items: List[Dict] = []

    qty_pattern = re.compile(r"(?P<qty>\d+(?:\.\d+)?)\s*(kg|kilogram)", re.IGNORECASE)
    ton_pattern = re.compile(r"(?P<tons>\d+(?:\.\d+)?)\s*(ton|tons|tonne)", re.IGNORECASE)
    distance_pattern = re.compile(r"(?P<dist>\d+(?:\.\d+)?)\s*(km|kilometer|kilometre)", re.IGNORECASE)
    amount_pattern = re.compile(r"\$?\s*(?P<amt>\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*(usd|$)?", re.IGNORECASE)

    for line in lines:
        has_match = False
        lower = line.lower()
        if "supplier" in lower or "vendor" in lower or lower.startswith("from:"):
            current_supplier = line.split(":", 1)[1].strip() if ":" in line else line.strip() or supplier
            continue

        item: Dict = {"supplier": current_supplier, "description": line}

        qty_match = qty_pattern.search(line)
        if qty_match:
            item["qty_kg"] = float(qty_match.group("qty"))
            has_match = True

        ton_match = ton_pattern.search(line)
        if ton_match:
            item["weight_tons"] = float(ton_match.group("tons"))
            has_match = True

        dist_match = distance_pattern.search(line)
        if dist_match:
            item["distance_km"] = float(dist_match.group("dist"))
            has_match = True

        amt_match = amount_pattern.search(line)
        if amt_match:
            item["amount_usd"] = _clean_amount(amt_match.group("amt"))
            has_match = True

        if has_match:
            items.append(item)

    # If nothing matched, produce a single generic item so downstream logic can still run
    if not items and text.strip():
        items.append({"supplier": supplier, "description": lines[0] if lines else "Unknown item"})

    return items
