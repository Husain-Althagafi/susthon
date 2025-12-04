import io
import json
import sys
from pathlib import Path
from typing import List, Optional

import pandas as pd
import streamlit as st

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.append(str(APP_ROOT))

from src.aggregate import aggregate, recommendation
from src.emissions import compute_emissions
from src.factors import load_factors
from src.ocr import extract_text
from src.parser import parse_invoice_text


def run_pipeline(text: str) -> Optional[dict]:
    if not text.strip():
        return None
    factors = load_factors()
    items = parse_invoice_text(text)
    enriched = [compute_emissions(item, factors) for item in items]
    total, df, by_supplier, by_category = aggregate(enriched)

    output_dir = APP_ROOT / "output"
    output_dir.mkdir(exist_ok=True)
    (output_dir / "parsed_data.json").write_text(json.dumps(enriched, indent=2))
    return {
        "items": enriched,
        "total": total,
        "df": df,
        "by_supplier": by_supplier,
        "by_category": by_category,
    }


def load_sample_invoice() -> str:
    sample_path = APP_ROOT / "data" / "sample_invoices" / "invoice1.txt"
    if sample_path.exists():
        return sample_path.read_text()
    return ""


def render_charts(by_supplier: pd.DataFrame, by_category: pd.DataFrame):
    if not by_supplier.empty:
        st.subheader("Emissions by Supplier")
        st.bar_chart(by_supplier.set_index("supplier")["emissions_kg"])

    if not by_category.empty:
        st.subheader("Emissions by Category")
        st.bar_chart(by_category.set_index("category")["emissions_kg"])


def render_table(by_supplier: pd.DataFrame):
    if by_supplier.empty:
        st.info("No supplier data parsed yet.")
        return
    display_cols = ["supplier", "emissions_kg", "score", "comments"]
    st.subheader("Supplier Scores")
    st.dataframe(by_supplier[display_cols].sort_values("emissions_kg", ascending=False))


def main():
    st.set_page_config(page_title="Scope 3 Estimator", layout="wide")
    st.title("Scope 3 Emissions Estimation MVP")
    st.write("Upload an invoice (PDF/image/text), parse it, and estimate Scope 3 emissions.")

    col1, col2 = st.columns(2)
    with col1:
        uploaded = st.file_uploader("Upload invoice", type=["pdf", "png", "jpg", "jpeg", "txt"])
    with col2:
        use_sample = st.button("Use sample invoice")

    invoice_text = ""

    if uploaded:
        content = uploaded.getvalue()
        invoice_text = extract_text(io.BytesIO(content), filename=uploaded.name)
    elif use_sample:
        invoice_text = load_sample_invoice()

    if invoice_text:
        st.text_area("Extracted text", invoice_text, height=200)
        result = run_pipeline(invoice_text)
        if result:
            st.metric("Total emissions (kg CO2e)", f"{result['total']:.2f}")
            render_charts(result["by_supplier"], result["by_category"])
            render_table(result["by_supplier"])
            st.subheader("Parsed items")
            st.json(result["items"])
            st.subheader("Recommendation")
            st.success(recommendation(result["by_supplier"]))
    else:
        st.info("Upload a file or click 'Use sample invoice' to get started.")


if __name__ == "__main__":
    main()
