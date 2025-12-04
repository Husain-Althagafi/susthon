from typing import Dict, Optional

ANALYSES: Dict[str, Dict] = {}


def save_analysis(invoice_id: str, analysis: Dict) -> None:
    ANALYSES[invoice_id] = analysis


def get_analysis(invoice_id: str) -> Optional[Dict]:
    return ANALYSES.get(invoice_id)
