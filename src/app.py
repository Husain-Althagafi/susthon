import sys
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.append(str(APP_ROOT))

from src.llm_client import LLMClientError, generate_reply
from src.pipeline import run_pipeline
from src.prompts import build_prompt


def ensure_state():
    if "analysis" not in st.session_state:
        st.session_state.analysis = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []


def load_sample_path() -> Path:
    return APP_ROOT / "data" / "sample_invoices" / "invoice1.txt"


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
    display_cols = ["supplier", "emissions_kg", "spend", "score", "comments"]
    st.subheader("Supplier Scores")
    st.dataframe(by_supplier[display_cols].sort_values("emissions_kg", ascending=False))


def main():
    ensure_state()
    st.set_page_config(page_title="Scope 3 Estimator + Chat", layout="wide")
    st.title("Scope 3 Emissions Estimation + Chat")
    st.write("Upload an invoice, estimate Scope 3 emissions, then ask questions about the results or anything else.")

    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded = st.file_uploader("Upload invoice", type=["pdf", "png", "jpg", "jpeg", "txt"])
        analyze_click = st.button("Analyze invoice")
    with col2:
        use_sample = st.button("Use sample invoice")

    if analyze_click and uploaded:
        suffix = Path(uploaded.name).suffix or ".bin"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded.getvalue())
            tmp_path = Path(tmp.name)
        st.session_state.analysis = run_pipeline(str(tmp_path))
        st.session_state.chat_history = []
    elif use_sample:
        st.session_state.analysis = run_pipeline(str(load_sample_path()))
        st.session_state.chat_history = []

    analysis = st.session_state.analysis
    if analysis:
        st.success(f"Analyzed invoice {analysis['invoice_id']}")
        summary_cols = st.columns(3)
        summary = analysis["summary"]
        summary_cols[0].metric("Total emissions (kg CO2e)", f"{summary['total_emissions_kg']:.2f}")
        summary_cols[1].metric("Total spend", f"${summary['total_spend']:.2f}")
        summary_cols[2].metric("Top supplier", analysis["hotspots"]["top_supplier"] or "N/A")

        by_supplier_df = pd.DataFrame(analysis["by_supplier"])
        by_category_df = pd.DataFrame(analysis["by_category"])

        render_charts(by_supplier_df, by_category_df)
        render_table(by_supplier_df)

        st.subheader("Parsed items")
        st.json(analysis["items"])

        st.subheader("Chat with the assistant")

        # Quick suggestion buttons
        suggestion_cols = st.columns(3)
        suggestions = [
            "Where are my biggest hotspots?",
            "Which supplier should I focus on first?",
            "How could I reduce emissions by 20%?"
        ]
        for col, text in zip(suggestion_cols, suggestions):
            if col.button(text):
                st.session_state.chat_history.append({"role": "user", "content": text})
                try:
                    reply = generate_reply(build_prompt(text, analysis))
                    st.session_state.chat_history.append({"role": "assistant", "content": reply})
                except LLMClientError as exc:
                    st.error(str(exc))

        # Free-form chat input
        if prompt := st.chat_input("Ask about this invoice or anything else"):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            try:
                reply = generate_reply(build_prompt(prompt, analysis))
                st.session_state.chat_history.append({"role": "assistant", "content": reply})
            except LLMClientError as exc:
                st.error(str(exc))

        # Render chat history after updates so newest messages show immediately
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
    else:
        st.info("Upload a file and click Analyze, or use the sample invoice to get started.")


if __name__ == "__main__":
    main()
