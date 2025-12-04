from typing import Dict, List, Tuple

import pandas as pd


def aggregate(items: List[Dict]) -> Tuple[float, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = pd.DataFrame(items)
    if df.empty:
        return 0.0, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    total = df["emissions_kg"].sum()
    by_supplier = df.groupby("supplier", dropna=False)["emissions_kg"].sum().reset_index()
    by_category = df.groupby("category", dropna=False)["emissions_kg"].sum().reset_index()

    max_emissions = by_supplier["emissions_kg"].max()
    # Normalize to 0-100 where higher emissions = lower score
    by_supplier["score"] = by_supplier["emissions_kg"].apply(
        lambda x: round(100 * (1 - (x / max_emissions)), 2) if max_emissions else 0
    )
    by_supplier["comments"] = by_supplier["score"].apply(
        lambda s: "High impact, prioritize reduction" if s < 40 else "Moderate" if s < 70 else "Lower impact"
    )

    return total, df, by_supplier, by_category


def recommendation(by_supplier: pd.DataFrame) -> str:
    if by_supplier.empty:
        return "No suppliers detected."
    worst_row = by_supplier.sort_values("emissions_kg", ascending=False).iloc[0]
    supplier = worst_row["supplier"]
    return f"Focus decarbonization efforts on {supplier} to reduce Scope 3 emissions."
