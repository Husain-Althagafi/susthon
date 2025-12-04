from typing import Dict, List, Tuple

import pandas as pd


def aggregate(items: List[Dict]) -> Tuple[float, float, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = pd.DataFrame(items)
    if df.empty:
        return 0.0, 0.0, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    df["amount_usd"] = df.get("amount_usd", 0).fillna(0)
    total_emissions = df["emissions_kg"].sum()
    total_spend = df["amount_usd"].sum()

    by_supplier = (
        df.groupby("supplier", dropna=False)
        .agg(emissions_kg=("emissions_kg", "sum"), spend=("amount_usd", "sum"))
        .reset_index()
    )
    by_category = df.groupby("category", dropna=False)["emissions_kg"].sum().reset_index()

    max_emissions = by_supplier["emissions_kg"].max() if not by_supplier.empty else 0
    by_supplier["score"] = by_supplier["emissions_kg"].apply(
        lambda x: round(100 * (1 - (x / max_emissions)), 2) if max_emissions else 0
    )
    by_supplier["comments"] = by_supplier["score"].apply(
        lambda s: "High impact, prioritize reduction" if s < 40 else "Moderate" if s < 70 else "Lower impact"
    )

    return total_emissions, total_spend, df, by_supplier, by_category


def recommendation(by_supplier: pd.DataFrame) -> str:
    if by_supplier.empty:
        return "No suppliers detected."
    worst_row = by_supplier.sort_values("emissions_kg", ascending=False).iloc[0]
    supplier = worst_row["supplier"]
    return f"Focus decarbonization efforts on {supplier} to reduce Scope 3 emissions."


def build_analysis(invoice_id: str, items: List[Dict]) -> Dict:
    total, total_spend, df, by_supplier, by_category = aggregate(items)
    top_supplier = by_supplier.sort_values("emissions_kg", ascending=False).iloc[0]["supplier"] if not by_supplier.empty else None
    top_category = by_category.sort_values("emissions_kg", ascending=False).iloc[0]["category"] if not by_category.empty else None

    return {
        "invoice_id": invoice_id,
        "summary": {
            "total_emissions_kg": round(total, 2),
            "currency": "USD",
            "total_spend": round(float(total_spend), 2),
        },
        "by_supplier": by_supplier.to_dict(orient="records") if not by_supplier.empty else [],
        "by_category": by_category.to_dict(orient="records") if not by_category.empty else [],
        "hotspots": {"top_supplier": top_supplier, "top_category": top_category},
        "items": items,
    }
