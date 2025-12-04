from typing import Optional


KEYWORD_MAP = {
    "steel": ["steel", "coil", "beam", "rebar"],
    "transport": ["freight", "transport", "shipping", "truck", "rail", "ship"],
    "packaging": ["package", "packaging", "pallet", "box", "carton"],
}


def categorize(description: str) -> Optional[str]:
    desc = (description or "").lower()
    for category, keywords in KEYWORD_MAP.items():
        if any(word in desc for word in keywords):
            return category
    return None
