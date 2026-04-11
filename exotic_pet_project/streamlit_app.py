import streamlit as st
import pandas as pd

from src.data_processing import load_and_prepare_data
from src.visualizations import (
    plot_sentiment_distribution,
    plot_sentiment_by_platform,
    plot_theme_counts,
    plot_wordcloud
)
from src.wildlife_nlp import extract_entities, predict_risk
from src.llm_classifier import classify_themes_llm

# ----------------------------------
# CONFIG
# ----------------------------------
st.set_page_config(layout="wide", page_title="Exotic Pet Intelligence")

st.title("🐾 Exotic Pet Trade Intelligence Dashboard")

# ----------------------------------
# CACHING (VERY IMPORTANT)
# ----------------------------------
@st.cache_data(show_spinner=False)
def cached_llm_classification(texts, model):
    return classify_themes_llm(texts, model=model)

@st.cache_data(show_spinner=False)
def cached_risk(texts):
    return predict_risk(texts)

@st.cache_data(show_spinner=False)
def cached_entities(texts):
    return extract_entities(texts)

# ----------------------------------
# FILE UPLOAD
# ----------------------------------
file = st.file_uploader("Upload dataset (CSV)", type=["csv"])

if not file:
    st.info("Upload a dataset to begin analysis")
    st.stop()

df = load_and_prepare_data(file)

# ----------------------------------
# TABS
# ----------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Sentiment",
    "🌍 Themes",
    "🧠 NLP",
    "⚠️ Risk",
    "🤖 LLM"
])

# ----------------------------------
# SENTIMENT TAB
# ----------------------------------
with tab1:
    st.subheader("Sentiment Distribution")
    st.plotly_chart(plot_sentiment_distribution(df), use_container_width=True)

    if "platform" in df.columns:
        st.subheader("Sentiment by Platform")
        st.plotly_chart(plot_sentiment_by_platform(df), use_container_width=True)

# ----------------------------------
# THEMES TAB
# ----------------------------------
with tab2:
    st.subheader("Theme Frequency")
    st.plotly_chart(plot_theme_counts(df), use_container_width=True)

    st.subheader("Word Cloud")

    fig = plot_wordcloud(df["text_content"])
    st.pyplot(fig)

# ----------------------------------
# NLP TAB
# ----------------------------------
with tab3:
    st.subheader("Entity Extraction")

    entities = cached_entities(df["text_content"])
    st.dataframe(entities.head(50), use_container_width=True)

# ----------------------------------
# RISK TAB
# ----------------------------------
with tab4:
    st.subheader("Risk Classification")

    risk_df = cached_risk(df["text_content"])

    st.dataframe(risk_df.head(50), use_container_width=True)

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "High Risk %",
        round((risk_df["risk_label"] == "high").mean() * 100, 2)
    )
    col2.metric(
        "Medium Risk %",
        round((risk_df["risk_label"] == "medium").mean() * 100, 2)
    )
    col3.metric(
        "Low Risk %",
        round((risk_df["risk_label"] == "low").mean() * 100, 2)
    )

    # Export Risk
    st.download_button(
        label="Download Risk Results",
        data=risk_df.to_csv(index=False),
        file_name="risk_results.csv",
        mime="text/csv"
    )

# ----------------------------------
# LLM TAB (FIXED + PRODUCTION READY)
# ----------------------------------
with tab5:
    st.subheader("LLM Theme Classification")

    mode = st.radio(
        "Choose Mode",
        ["Sample (Fast & Cheap)", "Full Dataset (Slow & Expensive)"],
        horizontal=True
    )

    model_name = st.text_input("Model", value="gpt-4o-mini")

    sample_size = st.slider(
        "Sample size",
        min_value=5,
        max_value=min(200, len(df)),
        value=min(50, len(df))
    )

    if st.button("Run LLM Classification"):
        with st.spinner("Running LLM classification..."):
            if mode == "Full Dataset (Slow & Expensive)":
                working_df = df.copy()
            else:
                working_df = df.head(sample_size).copy()

            labels, errors = cached_llm_classification(
                tuple(working_df["text_content"].astype(str).tolist()),
                model_name,
            )

            working_df["llm_theme"] = labels
            working_df["llm_error"] = errors

            st.dataframe(
                working_df[["text_content", "llm_theme", "llm_error"]],
                use_container_width=True
            )

            failed = (working_df["llm_theme"] == "LLM_Error").sum()
            if failed:
                st.error(f"{failed} row(s) failed. Check the llm_error column.")
            else:
                st.success("Classification complete.")

            st.download_button(
                label="Download LLM Results",
                data=working_df.to_csv(index=False),
                file_name="llm_results.csv",
                mime="text/csv"
            )

# ----------------------------------
# GLOBAL EXPORT (FULL DATA)
# ----------------------------------
st.divider()

st.subheader("📥 Export Full Processed Dataset")

st.download_button(
    label="Download Full Dataset",
    data=df.to_csv(index=False),
    file_name="processed_dataset.csv",
    mime="text/csv"
)