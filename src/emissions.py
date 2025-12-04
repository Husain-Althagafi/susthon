from typing import Dict

from .categorize import categorize


def compute_emissions(item: Dict, factors: Dict[str, float]) -> Dict:
    enriched = dict(item)
    category = item.get("category") or categorize(item.get("description", ""))
    enriched["category"] = category or "other"

    qty_kg = item.get("qty_kg")
    amount_usd = item.get("amount_usd")
    weight_tons = item.get("weight_tons")
    distance_km = item.get("distance_km")

    emissions = 0.0

    if enriched["category"] == "steel" and qty_kg:
        emissions = qty_kg * factors["steel_per_kg"]
    elif enriched["category"] == "packaging" and qty_kg:
        emissions = qty_kg * factors["packaging_per_kg"]
    elif enriched["category"] == "transport" and weight_tons and distance_km:
        emissions = weight_tons * distance_km * factors["transport_per_tkm"]
    elif amount_usd is not None:
        emissions = amount_usd * factors["other_per_usd"]

    enriched["emissions_kg"] = round(emissions, 2)
    return enriched
