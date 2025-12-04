import sys
import tempfile
from pathlib import Path

import altair as alt
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
    if "chat_pending" not in st.session_state:
        st.session_state.chat_pending = False
    if "chat_status" not in st.session_state:
        st.session_state.chat_status = ""
    if "chat_pending" not in st.session_state:
        st.session_state.chat_pending = False


def load_sample_path() -> Path:
    return APP_ROOT / "data" / "sample_invoices" / "invoice1.txt"


def _styled_bar_chart(df: pd.DataFrame, x_field: str, y_field: str, title: str):
    # Build an Altair bar chart with tooltips and soft colors
    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X(x_field, sort="-y", title=""),
            y=alt.Y(y_field, title="kg CO2e"),
            tooltip=[x_field, alt.Tooltip(y_field, format=",")],
            color=alt.value("#38bdf8"),
        )
        .properties(title=title, height=260)
    )
    return chart


def render_charts(by_supplier: pd.DataFrame, by_category: pd.DataFrame):
    c1, c2 = st.columns(2)
    with c1:
        if not by_supplier.empty:
            st.markdown("<div class='card'><strong>Emissions by Supplier</strong></div>", unsafe_allow_html=True)
            st.altair_chart(_styled_bar_chart(by_supplier, "supplier", "emissions_kg", "By Supplier"), use_container_width=True)
        else:
            st.info("No supplier data parsed.")
    with c2:
        if not by_category.empty:
            st.markdown("<div class='card'><strong>Emissions by Category</strong></div>", unsafe_allow_html=True)
            st.altair_chart(_styled_bar_chart(by_category, "category", "emissions_kg", "By Category"), use_container_width=True)
        else:
            st.info("No category data parsed.")


def render_table(by_supplier: pd.DataFrame):
    if by_supplier.empty:
        st.info("No supplier data parsed yet.")
        return
    display_cols = ["supplier", "emissions_kg", "spend", "score", "comments"]
    st.markdown("##### Supplier Scores")
    st.dataframe(by_supplier[display_cols].sort_values("emissions_kg", ascending=False), use_container_width=True)


def handle_chat_message(text: str, analysis: dict):
    if st.session_state.chat_pending:
        st.warning("Please wait for the previous reply to finish.")
        return

    st.session_state.chat_pending = True
    st.session_state.chat_history.append({"role": "user", "content": text})
    # Add a placeholder assistant message for immediate feedback
    st.session_state.chat_history.append({"role": "assistant", "content": "…"})
    st.session_state.chat_status = "Assistant is thinking..."
    status = st.empty()
    status.info(st.session_state.chat_status)
    try:
        reply = generate_reply(build_prompt(text, analysis))
        # Replace last placeholder with real reply
        st.session_state.chat_history[-1] = {"role": "assistant", "content": reply}
        st.session_state.chat_status = "Reply received."
        status.success(st.session_state.chat_status)
    except LLMClientError as exc:
        st.session_state.chat_history[-1] = {"role": "assistant", "content": f"(error) {exc}"}
    finally:
        status.empty()
        st.session_state.chat_pending = False
        st.session_state.chat_status = ""


def main():
    ensure_state()
    st.set_page_config(page_title="Scope 3 Estimator + Chat", layout="wide")

    st.markdown(
        """
        <style>
        .hero {
            padding: 20px 24px;
            border-radius: 14px;
            background: linear-gradient(135deg, #0f172a, #1e293b);
            color: #e2e8f0;
            margin-bottom: 14px;
        }
        .hero h1 {margin: 0 0 8px 0; font-size: 28px;}
        .hero p {margin: 0; color: #cbd5e1;}
        .card {
            background: #0b1528;
            border: 1px solid #1f2a44;
            border-radius: 12px;
            padding: 16px;
            color: #e2e8f0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="hero">
            <h1>Scope 3 Emissions Estimator + Chat</h1>
            <p>Upload an invoice, estimate emissions, and ask follow-up questions with the assistant.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("##### 1) Upload invoice")
        uploaded = st.file_uploader("PDF, image, or text invoice", type=["pdf", "png", "jpg", "jpeg", "txt"])
        analyze_click = st.button("Analyze invoice", type="primary", use_container_width=True)
    with col2:
        st.markdown("##### 2) Or try a sample")
        use_sample = st.button("Use sample invoice", use_container_width=True)

    if analyze_click and uploaded:
        suffix = Path(uploaded.name).suffix or ".bin"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded.getvalue())
            tmp_path = Path(tmp.name)
        st.session_state.analysis = run_pipeline(str(tmp_path))
        st.session_state.chat_history = []
        st.session_state.chat_status = ""
    elif use_sample:
        st.session_state.analysis = run_pipeline(str(load_sample_path()))
        st.session_state.chat_history = []
        st.session_state.chat_status = ""

    analysis = st.session_state.analysis
    if analysis:
        summary = analysis["summary"]
        hotspots = analysis["hotspots"]

        st.markdown(
            f"<div class='card'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
            f"<div><span style='opacity:0.8;'>Invoice ID</span><br><strong>{analysis['invoice_id']}</strong></div>"
            f"<div style='padding:6px 10px;border:1px solid #1f2a44;border-radius:8px;font-size:12px;'>Analyzed</div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )

        st.markdown("#### Summary")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total emissions (kg CO2e)", f"{summary['total_emissions_kg']:.2f}")
        m2.metric("Total spend (USD)", f"{summary['total_spend']:.2f}")
        m3.metric("Top supplier", hotspots["top_supplier"] or "N/A")

        st.markdown(
            f"""
            <div class="card">
                <strong>Hotspots & hints</strong><br>
                • Top supplier: {hotspots['top_supplier'] or 'N/A'}<br>
                • Top category: {hotspots['top_category'] or 'N/A'}<br>
                <span style="color:#94a3b8;">Tip: focus on the top supplier/category for quickest impact.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        by_supplier_df = pd.DataFrame(analysis["by_supplier"])
        by_category_df = pd.DataFrame(analysis["by_category"])

        st.markdown("#### Emissions breakdown")
        top_cards = st.columns(2)
        top_sup_val = (
            float(by_supplier_df.sort_values("emissions_kg", ascending=False).iloc[0]["emissions_kg"])
            if not by_supplier_df.empty else 0
        )
        top_cat_val = (
            float(by_category_df.sort_values("emissions_kg", ascending=False).iloc[0]["emissions_kg"])
            if not by_category_df.empty else 0
        )
        top_cards[0].markdown(
            f"<div class='card'><strong>Top supplier</strong><br>{hotspots['top_supplier'] or 'N/A'}"
            f"<div style='color:#94a3b8;font-size:12px;'>~ {top_sup_val:.0f} kg CO2e</div></div>",
            unsafe_allow_html=True,
        )
        top_cards[1].markdown(
            f"<div class='card'><strong>Top category</strong><br>{hotspots['top_category'] or 'N/A'}"
            f"<div style='color:#94a3b8;font-size:12px;'>~ {top_cat_val:.0f} kg CO2e</div></div>",
            unsafe_allow_html=True,
        )

        render_charts(by_supplier_df, by_category_df)

        render_table(by_supplier_df)

        with st.expander("Parsed items (raw)", expanded=False):
            st.json(analysis["items"])

        st.markdown("#### Chat with the assistant")

        # Quick suggestion buttons
        suggestion_cols = st.columns(3)
        suggestions = [
            "Where are my biggest hotspots?",
            "Which supplier should I focus on first?",
            "How could I reduce emissions by 20%?"
        ]
        for col, text in zip(suggestion_cols, suggestions):
            if col.button(text, disabled=st.session_state.chat_pending):
                handle_chat_message(text, analysis)

        # Free-form chat input
        prompt = st.chat_input("Ask about this invoice or anything else", disabled=st.session_state.chat_pending)
        if prompt:
            handle_chat_message(prompt, analysis)

        # Render chat history after updates so newest messages show immediately
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
            if st.session_state.chat_status:
                st.caption(st.session_state.chat_status)
        if st.button("Clear chat", type="secondary", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.chat_status = ""
    else:
        st.info("Upload a file and click Analyze, or use the sample invoice to get started.")


if __name__ == "__main__":
    main()
