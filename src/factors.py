import json
from pathlib import Path
from typing import Dict

DEFAULT_FACTORS = {
    "steel_per_kg": 2.0,
    "packaging_per_kg": 1.5,
    "transport_per_tkm": 0.06,
    "other_per_usd": 0.4,
}


def load_factors(path: str = "data/emission_factors.json") -> Dict[str, float]:
    fp = Path(path)
    if fp.exists():
        try:
            return json.loads(fp.read_text())
        except Exception:
            return DEFAULT_FACTORS
    return DEFAULT_FACTORS
