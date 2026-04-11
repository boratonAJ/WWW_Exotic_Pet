import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

from src.wildlife_nlp import (
    extract_wildlife_entities,
    predict_conservation_risk,
    train_conservation_risk_classifier,
)

# Optional stats
try:
    import pingouin as pg

    PINGOUIN_AVAILABLE = True
except Exception:
    PINGOUIN_AVAILABLE = False

STATS = PINGOUIN_AVAILABLE

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="Exotic Pet Research Dashboard", layout="wide")

st.markdown(
    """
    <style>
        html, body, [class*="css"]  {
            font-family: "Georgia", "Times New Roman", serif;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(123, 45, 55, 0.28), transparent 24%),
                radial-gradient(circle at top right, rgba(84, 14, 78, 0.22), transparent 24%),
                radial-gradient(circle at bottom center, rgba(35, 21, 48, 0.34), transparent 28%),
                linear-gradient(180deg, #120b16 0%, #1a111f 35%, #24162b 100%);
            color: #f8f4f7;
        }

        .main .block-container {
            padding-top: 1.2rem;
            padding-bottom: 2.5rem;
            max-width: 1400px;
        }

        .hero-card {
            padding: 1.4rem 1.6rem 1.1rem 1.6rem;
            border-radius: 22px;
            background: linear-gradient(180deg, rgba(27, 17, 33, 0.88), rgba(18, 11, 22, 0.82));
            border: 1px solid rgba(204, 163, 177, 0.18);
            box-shadow: 0 18px 44px rgba(0, 0, 0, 0.38);
            backdrop-filter: blur(12px);
            margin-bottom: 1rem;
            text-align: center;
        }

        .hero-kicker {
            text-transform: uppercase;
            letter-spacing: 0.22em;
            font-size: 0.76rem;
            color: #d9b5c3;
            margin-bottom: 0.25rem;
            font-weight: 700;
        }

        .hero-title {
            font-size: 2.25rem;
            line-height: 1.1;
            font-weight: 800;
            color: #fff7fb;
            margin: 0.1rem 0 0.35rem 0;
        }

        .hero-subtitle {
            color: #f0dfe7;
            font-size: 0.98rem;
            max-width: 900px;
            margin: 0 auto;
        }

        h1, h2, h3, h4, h5, h6, p, li, label, span, div {
            color: inherit;
        }

        .stMarkdown, .stMarkdown p {
            color: #f5ebf0;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0.6rem;
            background: rgba(20, 12, 24, 0.82);
            padding: 0.45rem;
            border-radius: 16px;
            border: 1px solid rgba(204, 163, 177, 0.14);
            box-shadow: 0 10px 28px rgba(0, 0, 0, 0.22);
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 12px;
            padding: 0.55rem 1.15rem;
            font-weight: 600;
            color: #f4e8ee !important;
            border: 1px solid rgba(205, 171, 182, 0.12);
            background: linear-gradient(180deg, rgba(46, 30, 46, 0.9), rgba(26, 17, 26, 0.9));
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05);
            transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
        }

        .stTabs [data-baseweb="tab"]:hover {
            transform: translateY(-1px);
            box-shadow: 0 10px 22px rgba(0, 0, 0, 0.22);
        }

        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #8a294c 0%, #b33b67 100%) !important;
            color: white !important;
            border-color: rgba(255, 213, 227, 0.3);
        }

        div[data-testid="stMetric"] {
            background: linear-gradient(180deg, rgba(36, 22, 43, 0.92), rgba(24, 15, 29, 0.92));
            border: 1px solid rgba(205, 171, 182, 0.16);
            padding: 0.9rem 1rem;
            border-radius: 16px;
            box-shadow: 0 10px 28px rgba(0, 0, 0, 0.28);
        }

        div[data-testid="stDataFrame"] {
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid rgba(205, 171, 182, 0.14);
            box-shadow: 0 10px 28px rgba(0, 0, 0, 0.28);
        }

        div[data-testid="stButton"] > button,
        div[data-testid="stDownloadButton"] > button {
            border-radius: 999px !important;
            border: 1px solid rgba(205, 171, 182, 0.2) !important;
            background: linear-gradient(135deg, #6d1f3d 0%, #9a2f58 100%) !important;
            color: white !important;
            font-weight: 700 !important;
            padding: 0.55rem 1rem !important;
            box-shadow: 0 10px 24px rgba(109, 31, 61, 0.28);
        }

        div[data-testid="stDownloadButton"] > button:hover,
        div[data-testid="stButton"] > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 12px 28px rgba(154, 47, 88, 0.34);
        }

        div[data-testid="stSelectbox"] {
            background: rgba(34, 21, 36, 0.88);
            border-radius: 14px;
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #18101d 0%, #110b15 100%);
            border-right: 1px solid rgba(205, 171, 182, 0.12);
        }

        .stSidebar, .stSidebar label, .stSidebar p, .stSidebar span {
            color: #f7eef3 !important;
        }

        .stAlert {
            border-radius: 14px;
        }
    </style>
    <div class="hero-card">
        <div class="hero-kicker">Research Dashboard</div>
        <div class="hero-title">Exotic Pet Trade Research Dashboard</div>
        <div class="hero-subtitle">Understand online discourse on exotic pets: sentiment, themes, species risk, platform differences, language patterns, and high-priority posts for WWF intervention.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# LOAD DATA
# -----------------------------
st.sidebar.header("Upload Data")
uploaded_file = st.sidebar.file_uploader("Upload CSV", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
else:
    st.warning("Please upload your dataset.")
    st.stop()  # prevents code below from running
    raise SystemExit

# -----------------------------
# TEXT COLUMN DETECTION
# -----------------------------
TEXT_COL = None
for candidate in ["text_content", "text", "snippet"]:
    if candidate in df.columns:
        TEXT_COL = candidate
        break

if TEXT_COL is None:
    st.error("No text column found (expected one of: text_content, text, snippet).")
    st.stop()

if TEXT_COL != "text_content":
    df["text_content"] = df[TEXT_COL]
    TEXT_COL = "text_content"

# -----------------------------
# SENTIMENT ANALYSIS
# -----------------------------
analyzer = SentimentIntensityAnalyzer()

def get_sentiment(text):
    return analyzer.polarity_scores(str(text))["compound"]

df[TEXT_COL] = df[TEXT_COL].fillna("")

# Prefer provided sentiment score if available.
if "sentiment_score" in df.columns:
    df["sentiment"] = pd.to_numeric(df["sentiment_score"], errors="coerce").fillna(0.0)
else:
    df["sentiment"] = df[TEXT_COL].apply(get_sentiment)

def label_sentiment(score):
    if score > 0.05:
        return "Positive"
    elif score < -0.05:
        return "Negative"
    else:
        return "Neutral"

df["sentiment_label"] = df["sentiment"].apply(label_sentiment)

# -----------------------------
# STANCE CLASSIFICATION (Simple)
# -----------------------------
df["stance"] = np.where(
    df["sentiment"] > 0.1,
    "Supportive",
    np.where(df["sentiment"] < -0.1, "Critical", "Neutral"),
)

# Compute conservation risk once so all tabs can safely reference these columns.
risk_classifier = train_conservation_risk_classifier(df[TEXT_COL].tolist())
risk_df = predict_conservation_risk(df[TEXT_COL].tolist(), risk_classifier)
df["conservation_risk_label"] = risk_df["risk_label"]
df["conservation_risk_score"] = risk_df["risk_score"]

tab_sentiment, tab_themes, tab_species, tab_platform, tab_language, tab_risk_triage, tab_experimental = st.tabs(
    ["1. Sentiment Landscape", "2. Themes & Motivations", "3. Species Risk", "4. Platform Intelligence", "5. Language Insights", "6. Risk Triage", "7. Experimental"]
)

# ==================== RESEARCH QUESTION 1: SENTIMENT LANDSCAPE ====================
with tab_sentiment:
    st.subheader("📊 Research Q1: How much is negative, neutral, or supportive?")
    st.caption("This tab answers the core sentiment landscape of exotic pet discourse.")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Comments", len(df))
    col2.metric("Avg Sentiment Score", round(df["sentiment"].mean(), 3))
    neg_pct = round((df['sentiment_label'] == 'Negative').mean() * 100, 1)
    pos_pct = round((df['sentiment_label'] == 'Positive').mean() * 100, 1)
    neu_pct = round((df['sentiment_label'] == 'Neutral').mean() * 100, 1)
    col3.metric("Negative %", f"{neg_pct}%")
    col4.metric("Positive %", f"{pos_pct}%")
    
    # Sentiment distribution
    st.subheader("Sentiment Distribution")
    fig_sent = px.histogram(
        df, 
        x="sentiment_label", 
        color="sentiment_label",
        category_orders={"sentiment_label": ["Negative", "Neutral", "Positive"]},
        title="How much discourse is negative, neutral, or supportive?"
    )
    st.plotly_chart(fig_sent, use_container_width=True)
    
    # Stance distribution (related but distinct)
    st.subheader("Stance Distribution")
    fig_stance = px.histogram(
        df, 
        x="stance", 
        color="stance",
        category_orders={"stance": ["Critical", "Neutral", "Supportive"]},
        title="Stance: Critical vs Neutral vs Supportive"
    )
    st.plotly_chart(fig_stance, use_container_width=True)
    
    # Optional: sentiment by platform if available
    if "platform" in df.columns:
        st.subheader("Sentiment by Platform")
        fig_platform = px.box(
            df, 
            x="platform", 
            y="sentiment",
            title="Platform Comparison (Sentiment Score Distribution)"
        )
        st.plotly_chart(fig_platform, use_container_width=True)

# ==================== RESEARCH QUESTION 2: THEMES & MOTIVATIONS ====================
with tab_themes:
    st.subheader("🎯 Research Q2: Which themes dominate?")
    st.caption("Multi-level evidence scoring: mention count, document frequency, cross-theme overlap, and platform prevalence.")
    
    # Define themes clearly
    keywords = {
        "legality": ["illegal", "law", "permit", "license", "regulated", "banned"],
        "safety": ["bite", "attack", "danger", "injury", "disease", "risk"],
        "welfare": ["suffer", "stress", "cruel", "captivity", "neglect", "care"],
        "conservation": ["endangered", "extinction", "ecosystem", "wildlife", "biodiversity"],
        "trade": ["for sale", "selling", "breeder", "expo", "shipping", "contact"],
    }

    # Multi-level evidence scoring
    theme_evidence = []
    for theme, words in keywords.items():
        df[theme] = df[TEXT_COL].str.contains("|".join(words), case=False, na=False)
        
        mentions = int(df[theme].sum())
        doc_freq = round(mentions / len(df) * 100, 1)  # % of documents mentioning theme
        risk_avg = df.loc[df[theme], "conservation_risk_score"].mean() if mentions > 0 else 0
        
        theme_evidence.append({
            "Theme": theme.capitalize(),
            "Mentions": mentions,
            "Document Frequency %": doc_freq,
            "Avg Risk Score": round(risk_avg, 2),
            "Risk Intensity": "High" if risk_avg >= 4 else "Medium" if risk_avg >= 2 else "Low"
        })
    
    theme_df = pd.DataFrame(theme_evidence).sort_values("Mentions", ascending=False)
    
    fig_theme = px.bar(
        theme_df, 
        x="Theme", 
        y="Mentions", 
        color="Avg Risk Score",
        title="Theme Prevalence with Risk Intensity",
        labels={"Mentions": "Number of posts", "Avg Risk Score": "Avg Conservation Risk"}
    )
    st.plotly_chart(fig_theme, use_container_width=True)
    
    st.subheader("Multi-Level Theme Evidence")
    st.dataframe(theme_df, use_container_width=True, hide_index=True)
    
    # Cross-theme overlap analysis
    st.subheader("Cross-Theme Overlap (Posts with Multiple Concerns)")
    df["theme_count"] = df[keywords.keys()].sum(axis=1)
    overlap_data = pd.DataFrame({
        "Themes Combined": ["1 Theme", "2 Themes", "3+ Themes"],
        "Post Count": [
            sum(df["theme_count"] == 1),
            sum(df["theme_count"] == 2),
            sum(df["theme_count"] >= 3)
        ]
    })
    overlap_data["Percentage"] = round(overlap_data["Post Count"] / len(df) * 100, 1)
    
    fig_overlap = px.bar(
        overlap_data,
        x="Themes Combined",
        y="Post Count",
        color="Percentage",
        title="Posts with Multiple Concurrent Themes (Higher complexity = riskier)",
        text="Percentage"
    )
    st.plotly_chart(fig_overlap, use_container_width=True)
    
    st.subheader("Theme Definitions")
    theme_defs = {
        "Legality": "Posts discussing laws, permits, regulations, bans, or legal status",
        "Safety": "Posts about physical risks: bites, attacks, disease, injuries",
        "Welfare": "Posts about animal care needs, suffering, stress, captivity conditions",
        "Conservation": "Posts about species endangerment, ecosystem impact, biodiversity",
        "Trade": "Posts about purchasing, breeding, shipping, or commercial channels",
    }
    for theme, definition in theme_defs.items():
        st.write(f"**{theme.upper()}**: {definition}")

# ==================== RESEARCH QUESTION 3: SPECIES RISK PROFILE ====================
with tab_species:
    st.subheader("🐅 Research Q3: Which species attract highest-risk discussions?")
    st.caption("Identify which species groups drive the most risky discourse.")
    
    # Species groups
    species_groups = {
        "Big Cats": ["tiger", "lion", "jaguar", "cheetah", "leopard", "serval"],
        "Primates": ["monkey", "chimpanzee", "gibbon", "lemur", "macaque"],
        "Parrots/Birds": ["parrot", "macaw", "cockatoo", "eagle", "falcon"],
        "Reptiles": ["python", "boa", "monitor", "iguana", "serpent"],
        "Other": []
    }
    
    # Count species and average risk
    species_risk_data = []
    for group, species_list in species_groups.items():
        if species_list:
            mask = df[TEXT_COL].str.contains("|".join(species_list), case=False, na=False)
            count = mask.sum()
            avg_risk = df.loc[mask, "conservation_risk_score"].mean() if count > 0 else 0
            high_risk_pct = round((df.loc[mask, "conservation_risk_label"] == "high").sum() / max(count, 1) * 100, 1) if count > 0 else 0
        else:
            count = len(df)
            avg_risk = df["conservation_risk_score"].mean()
            high_risk_pct = round((df["conservation_risk_label"] == "high").sum() / max(count, 1) * 100, 1) if count > 0 else 0
        
        species_risk_data.append({
            "Species Group": group,
            "Post Count": count,
            "Avg Risk Score": round(avg_risk, 2),
            "% High Risk": high_risk_pct
        })
    
    species_risk_df = pd.DataFrame(species_risk_data).sort_values("Post Count", ascending=False)
    
    fig_species = px.bar(
        species_risk_df,
        x="Species Group",
        y="Post Count",
        color="Avg Risk Score",
        title="Species Groups and Risk Profile",
        labels={"Post Count": "Posts mentioning group"}
    )
    st.plotly_chart(fig_species, use_container_width=True)
    
    st.subheader("Species Group Risk Details")
    st.dataframe(species_risk_df, use_container_width=True, hide_index=True)


    # High-risk examples
    high_risk = df[df["conservation_risk_label"] == "high"].head(5)
    if not high_risk.empty:
        st.subheader("High-Risk Post Examples")
        for idx, row in high_risk.iterrows():
            st.write(f"**{row['title'][:80]}...**" if "title" in row.index else "Post")
            st.info(f"Risk Score: {row['conservation_risk_score']:.2f} | {row['conservation_risk_label'].upper()}")

# ==================== RESEARCH QUESTION 4: PLATFORM INTELLIGENCE ====================
with tab_platform:
    st.subheader("🌐 Research Q4: How do platforms differ?")
    st.caption("Compare sentiment, themes, and content patterns across platforms.")
    
    if "platform" in df.columns:
        platforms = df["platform"].unique()
        
        # Sentiment by platform
        st.subheader("Sentiment Distribution by Platform")
        platform_sentiment = df.groupby(["platform", "sentiment_label"]).size().unstack(fill_value=0)
        fig_plat_sent = px.bar(
            platform_sentiment.reset_index().melt(id_vars="platform", var_name="Sentiment", value_name="Count"),
            x="platform",
            y="Count",
            color="Sentiment",
            barmode="group",
            title="Sentiment by Platform"
        )
        st.plotly_chart(fig_plat_sent, use_container_width=True)
        
        # Theme intensity by platform
        st.subheader("Theme Intensity by Platform")
        keywords = {
            "legality": ["illegal", "law", "permit", "license", "regulated", "banned"],
            "safety": ["bite", "attack", "danger", "injury", "disease", "risk"],
            "welfare": ["suffer", "stress", "cruel", "captivity", "neglect", "care"],
            "conservation": ["endangered", "extinction", "ecosystem", "wildlife", "biodiversity"],
            "trade": ["for sale", "selling", "breeder", "expo", "shipping", "contact"],
        }
        
        theme_by_platform = []
        for platform in platforms:
            platform_df = df[df["platform"] == platform]
            for theme, words in keywords.items():
                count = platform_df[TEXT_COL].str.contains("|".join(words), case=False, na=False).sum()
                pct = round(count / len(platform_df) * 100, 1) if len(platform_df) > 0 else 0
                theme_by_platform.append({"Platform": platform, "Theme": theme, "% of Posts": pct})
        
        theme_plat_df = pd.DataFrame(theme_by_platform)
        fig_plat_theme = px.bar(
            theme_plat_df,
            x="Theme",
            y="% of Posts",
            color="Platform",
            barmode="group",
            title="Theme Intensity by Platform"
        )
        st.plotly_chart(fig_plat_theme, use_container_width=True)
        
        # Theme-by-Platform Heatmap (relationship visualization)
        st.subheader("Theme-by-Platform Heatmap (Relationship Matrix)")
        pivot_theme_platform = theme_plat_df.pivot(index="Theme", columns="Platform", values="% of Posts").fillna(0)
        fig_heatmap = px.imshow(
            pivot_theme_platform,
            labels=dict(x="Platform", y="Theme", color="% of Posts"),
            title="Which platforms emphasize which themes? (Darker = higher %)",
            color_continuous_scale="RdYlGn_r"
        )
        st.plotly_chart(fig_heatmap, use_container_width=True)
        
        # Platform statistics table
        st.subheader("Platform Summary Statistics")
        platform_stats = []
        for platform in platforms:
            plat_data = df[df["platform"] == platform]
            platform_stats.append({
                "Platform": platform,
                "Post Count": len(plat_data),
                "Avg Sentiment": round(plat_data["sentiment"].mean(), 3),
                "% Negative": round((plat_data["sentiment_label"] == "Negative").mean() * 100, 1),
                "% Positive": round((plat_data["sentiment_label"] == "Positive").mean() * 100, 1),
                "Avg Risk Score": round(plat_data["conservation_risk_score"].mean(), 2)
            })
        
        platform_stats_df = pd.DataFrame(platform_stats)
        st.dataframe(platform_stats_df, use_container_width=True, hide_index=True)
    else:
        st.info("Platform column not found in data. Upload data that includes platform information.")

# ==================== RESEARCH QUESTION 5: LANGUAGE INSIGHTS ====================
with tab_language:
    st.subheader("💬 Research Q5: Which words/phrases dominate?")
    st.caption("Analyze top terms and language patterns by platform or stance.")
    
    # Option to segment by platform or stance
    segment_by = st.radio("Segment language patterns by:", ["Platform", "Stance"])
    
    if segment_by == "Platform" and "platform" in df.columns:
        platform_selected = st.selectbox("Select platform:", df["platform"].unique())
        plat_texts = df[df["platform"] == platform_selected][TEXT_COL].astype(str)
        
        if len(plat_texts) >= 5:
            try:
                vectorizer = CountVectorizer(stop_words="english", max_features=20)
                X = vectorizer.fit_transform(plat_texts)
                term_freq = np.asarray(X.sum(axis=0)).flatten()
                terms = vectorizer.get_feature_names_out()
                
                term_df = pd.DataFrame({
                    "Term": terms,
                    "Frequency": term_freq
                }).sort_values("Frequency", ascending=False)
                
                fig_terms = px.bar(
                    term_df.head(15),
                    x="Term",
                    y="Frequency",
                    title=f"Top Terms on {platform_selected}"
                )
                st.plotly_chart(fig_terms, use_container_width=True)
                
                st.subheader("Top Terms Table")
                st.dataframe(term_df.head(20), use_container_width=True, hide_index=True)
            except Exception as e:
                st.warning(f"Could not extract terms: {e}")
        else:
            st.info(f"Not enough posts on {platform_selected} for language analysis.")
    
    else:  # Segment by Stance
        stance_selected = st.selectbox("Select stance:", df["stance"].unique())
        stance_texts = df[df["stance"] == stance_selected][TEXT_COL].astype(str)
        
        if len(stance_texts) >= 5:
            try:
                vectorizer = CountVectorizer(stop_words="english", max_features=20)
                X = vectorizer.fit_transform(stance_texts)
                term_freq = np.asarray(X.sum(axis=0)).flatten()
                terms = vectorizer.get_feature_names_out()
                
                term_df = pd.DataFrame({
                    "Term": terms,
                    "Frequency": term_freq
                }).sort_values("Frequency", ascending=False)
                
                fig_terms = px.bar(
                    term_df.head(15),
                    x="Term",
                    y="Frequency",
                    title=f"Top Terms in {stance_selected} Comments"
                )
                st.plotly_chart(fig_terms, use_container_width=True)
                
                st.subheader("Top Terms Table")
                st.dataframe(term_df.head(20), use_container_width=True, hide_index=True)
            except Exception as e:
                st.warning(f"Could not extract terms: {e}")
        else:
            st.info(f"Not enough {stance_selected} posts for language analysis.")

# ==================== RESEARCH QUESTION 6: RISK TRIAGE ====================
with tab_risk_triage:
    st.subheader("⚠️ Research Q6: Which posts need WWF attention?")
    st.caption("High-priority posts combining trade signals with conservation or welfare risk.")
    
    # Define trade and risk keywords
    trade_keywords = ["for sale", "selling", "breeder", "expo", "shipping", "contact", "dm", "pm", "whatsapp", "telegram"]
    welfare_keywords = ["suffer", "cruel", "captivity", "stress", "neglect", "abuse"]
    conservation_keywords = ["endangered", "extinction", "ecosystem", "biodiversity", "poaching", "trafficking", "invasive", "cites"]
    
    # Create flags
    has_trade = df[TEXT_COL].str.contains("|".join(trade_keywords), case=False, na=False)
    has_welfare = df[TEXT_COL].str.contains("|".join(welfare_keywords), case=False, na=False)
    has_conservation = df[TEXT_COL].str.contains("|".join(conservation_keywords), case=False, na=False)
    has_legal = df[TEXT_COL].str.contains("|".join(["illegal", "ban", "permit", "cites"]), case=False, na=False)
    
    # High priority: trade + (welfare or conservation risk)
    high_priority = (has_trade) & ((has_welfare) | (has_conservation))
    
    st.subheader("Risk Profile Summary")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Posts with Trade Signals", int(has_trade.sum()))
    col2.metric("Posts with Welfare Concern", int(has_welfare.sum()))
    col3.metric("Posts with Conservation Concern", int(has_conservation.sum()))
    col4.metric("🚨 High Priority Posts", int(high_priority.sum()))
    
    st.subheader("High-Priority Posts (Trade + Welfare/Conservation Risk)")
    
    if high_priority.sum() > 0:
        priority_posts = df[high_priority].copy()
        priority_posts["has_welfare_risk"] = priority_posts[TEXT_COL].str.contains("|".join(welfare_keywords), case=False, na=False)
        priority_posts["has_conservation_risk"] = priority_posts[TEXT_COL].str.contains("|".join(conservation_keywords), case=False, na=False)
        priority_posts["risk_type"] = priority_posts.apply(
            lambda row: "Welfare+Trade" if row["has_welfare_risk"] and not row["has_conservation_risk"] 
                       else "Conservation+Trade" if row["has_conservation_risk"] and not row["has_welfare_risk"]
                       else "Welfare+Conservation+Trade",
            axis=1
        )
        
        # Display table
        display_cols = ["title"] if "title" in priority_posts.columns else [TEXT_COL]
        if "platform" in priority_posts.columns:
            display_cols.append("platform")
        if "source_url" in priority_posts.columns:
            display_cols.append("source_url")
        display_cols.extend(["sentiment_label", "conservation_risk_label", "risk_type"])
        
        st.dataframe(priority_posts[display_cols].head(50), use_container_width=True)
        
        # Download high-priority posts
        st.download_button(
            label="Download High-Priority Posts CSV",
            data=priority_posts.to_csv(index=False),
            file_name="high_priority_posts_wwf.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.info("No high-priority posts found combining trade and risk signals.")
    
    st.subheader("What Makes These Posts High Priority?")
    st.write("""
    - **Trade Signals**: Posts mentioning commercial channels (for sale, breeder, shipping, contact info)
    - **Welfare Risk**: Posts discussing animal suffering, cruelty, poor captivity conditions
    - **Conservation Risk**: Posts mentioning endangered species, extinction, ecosystem impact
    - **Combined Signal**: Post combines BOTH a trade signal AND a welfare/conservation concern
    
    These are the posts where WWF's messaging would be most strategic—intervening where people are discussing purchasing while simultaneously expressing concern about harm.
    """)
# ==================== TAB 7: EXPERIMENTAL & ADVANCED ANALYTICS ====================
with tab_experimental:
    st.write("👋 Welcome to the experimental and advanced analytics section. This tab includes wildlife NER, detailed risk analysis, intervention simulations, and ANOVA workflows.")
    
    # Subtab selection
    exp_subtab = st.radio("Select analysis type:", 
                          ["Wildlife NER & Risk Details", "Intervention Simulation", "ANOVA Analysis"],
                          horizontal=True)
    
    if exp_subtab == "Wildlife NER & Risk Details":
        st.subheader("🔍 Wildlife-Aware Named Entity Recognition")
        st.caption("Custom lexicon-based extraction for species, legal, welfare, conservation, safety, and trade signals.")

        ner_summary = extract_wildlife_entities(df[TEXT_COL].tolist())
        if ner_summary.empty:
            st.info("No wildlife entities found in the uploaded text.")
        else:
            ner_label_options = ["All"] + sorted(ner_summary["label"].unique().tolist())
            ner_label = st.selectbox("Filter entity label", ner_label_options, key="ner_label_filter")

            filtered_ner = ner_summary if ner_label == "All" else ner_summary[ner_summary["label"] == ner_label]
            st.dataframe(filtered_ner.head(30), use_container_width=True)

            if not filtered_ner.empty:
                fig_ner = px.bar(
                    filtered_ner.head(20),
                    x="entity",
                    y="count",
                    color="label",
                    title="Top Wildlife Entities",
                )
                st.plotly_chart(fig_ner, use_container_width=True)

            st.download_button(
                label="Download entity summary CSV",
                data=filtered_ner.to_csv(index=False).encode("utf-8"),
                file_name="wildlife_entity_summary.csv",
                mime="text/csv",
                use_container_width=True,
            )

        st.subheader("Conservation-Risk Classifier Details")
        risk_classifier = train_conservation_risk_classifier(df[TEXT_COL].tolist())
        risk_df_detail = predict_conservation_risk(df[TEXT_COL].tolist(), risk_classifier)

        risk_col1, risk_col2, risk_col3 = st.columns(3)
        risk_col1.metric("High-risk items", int((risk_df_detail["risk_label"] == "high").sum()))
        risk_col2.metric("Medium-risk items", int((risk_df_detail["risk_label"] == "medium").sum()))
        risk_col3.metric("Low-risk items", int((risk_df_detail["risk_label"] == "low").sum()))

        if getattr(risk_classifier, "accuracy", None) is not None:
            st.metric("Risk classifier accuracy", f"{risk_classifier.accuracy:.3f}")
        st.caption(f"Risk mode: {risk_classifier.mode}")

        fig_risk = px.histogram(
            risk_df_detail,
            x="risk_label",
            color="risk_label",
            category_orders={"risk_label": ["low", "medium", "high"]},
            title="Conservation Risk Distribution",
        )
        st.plotly_chart(fig_risk, use_container_width=True)

        st.download_button(
            label="Download risk predictions CSV",
            data=risk_df_detail.to_csv(index=False).encode("utf-8"),
            file_name="conservation_risk_predictions.csv",
            mime="text/csv",
            use_container_width=True,
        )

        high_risk_examples = risk_df_detail[risk_df_detail["risk_label"] == "high"].head(10)
        if not high_risk_examples.empty:
            st.subheader("High-Risk Examples")
            st.dataframe(high_risk_examples[["text", "risk_score", "matched_terms"]], use_container_width=True)
    
    
    elif exp_subtab == "Intervention Simulation":
        st.subheader("💬 Simulate Communication Intervention")
        st.caption("How could different framing messages affect sentiment toward exotic pets?")
        
        comment_type = st.selectbox(
            "Select intervention type:",
            ["Emotional", "Cognitive", "Conservation", "Behavioral", "Neutral"],
            key="condition_select",
        )

        comments = {
            "Emotional": "Exotic pets often suffer severe psychological distress in captivity.",
            "Cognitive": "Many exotic pets are illegal and require specialized care.",
            "Conservation": "Escaped exotic animals can destroy ecosystems.",
            "Behavioral": "Support conservation efforts instead of buying exotic pets.",
            "Neutral": "Exotic pets are non-domesticated animals kept in homes.",
        }
        st.info(f"**Sample message**: {comments[comment_type]}")

        condition_shift = {
            "Emotional": -0.18,
            "Cognitive": -0.10,
            "Conservation": -0.14,
            "Behavioral": -0.08,
            "Neutral": 0.00,
        }
        condition_keywords = {
            "Emotional": ["suffer", "stress", "pain", "cruel", "captivity", "abuse"],
            "Cognitive": ["illegal", "law", "permit", "regulated", "risk", "care"],
            "Conservation": ["ecosystem", "biodiversity", "endangered", "extinction", "wildlife"],
            "Behavioral": ["adopt", "responsibility", "training", "commitment", "rehome"],
            "Neutral": [],
        }

        selected_keywords = condition_keywords[comment_type]
        if selected_keywords:
            keyword_pattern = "|".join(selected_keywords)
            exposure_mask = df[TEXT_COL].str.contains(keyword_pattern, case=False, na=False)
        else:
            exposure_mask = pd.Series(False, index=df.index)

        delta = condition_shift[comment_type]
        df["sentiment_adjusted"] = np.where(exposure_mask, df["sentiment"] + delta, df["sentiment"])
        df["sentiment_adjusted"] = df["sentiment_adjusted"].clip(-1, 1)
        df["sentiment_adjusted_label"] = df["sentiment_adjusted"].apply(label_sentiment)

        before_after = pd.concat(
            [
                df[["sentiment_label"]].rename(columns={"sentiment_label": "label"}).assign(stage="Before"),
                df[["sentiment_adjusted_label"]].rename(columns={"sentiment_adjusted_label": "label"}).assign(stage="After"),
            ]
        )
        summary = before_after.groupby(["stage", "label"]).size().reset_index(name="count")

        fig_cond = px.bar(
            summary,
            x="label",
            y="count",
            color="stage",
            barmode="group",
            category_orders={"label": ["Negative", "Neutral", "Positive"]},
            title=f"Sentiment Impact: {comment_type} Intervention",
        )
        st.plotly_chart(fig_cond, use_container_width=True)

        impact_col1, impact_col2 = st.columns(2)
        impact_col1.metric("Posts Exposed To This Message", int(exposure_mask.sum()))
        impact_col2.metric("Avg Sentiment Shift", round(float((df["sentiment_adjusted"] - df["sentiment"]).mean()), 4))
    
    elif exp_subtab == "ANOVA Analysis":
        st.subheader("📊 Statistical Analysis (ANOVA)")
        st.caption("Run experimental ANOVA workflows on condition effects and outcomes.")
        
        exp_file = st.file_uploader("Upload Experimental Data (optional)", type=["csv"], key="exp_file")

        comments = {
            "Emotional": "Exotic pets often suffer severe psychological distress in captivity.",
            "Cognitive": "Many exotic pets are illegal and require specialized care.",
            "Conservation": "Escaped exotic animals can destroy ecosystems.",
            "Behavioral": "Support conservation efforts instead of buying exotic pets.",
            "Neutral": "Exotic pets are non-domesticated animals kept in homes.",
        }

        if exp_file:
            df_exp = pd.read_csv(exp_file)
        else:
            np.random.seed(42)
            df_exp = pd.DataFrame(
                {
                    "participant": np.arange(120),
                    "condition": np.random.choice(list(comments.keys()), 120),
                    "time": np.tile(["pre", "post"], 60),
                    "attitude": np.random.normal(3, 1, 120),
                    "desire": np.random.normal(3, 1, 120),
                    "civic_action": np.random.normal(3, 1, 120),
                }
            )

        st.write("**Data preview:**")
        st.dataframe(df_exp.head(10), use_container_width=True)

        st.subheader("Mixed ANOVA Results")
        required_mixed = {"participant", "condition", "time", "attitude"}
        if STATS:
            if required_mixed.issubset(df_exp.columns):
                try:
                    aov = pg.mixed_anova(
                        dv="attitude",
                        within="time",
                        between="condition",
                        subject="participant",
                        data=df_exp,
                    )
                    st.write("**Attitude ANOVA Results**")
                    st.dataframe(aov, use_container_width=True)
                except Exception as e:
                    st.error(f"ANOVA error: {e}")
            else:
                st.warning("Experimental data missing columns for mixed ANOVA.")
        else:
            st.warning("Install pingouin for ANOVA: pip install pingouin")

        st.subheader("Civic Action ANOVA")
        required_one_way = {"condition", "civic_action"}
        if STATS and required_one_way.issubset(df_exp.columns):
            try:
                aov2 = pg.anova(dv="civic_action", between="condition", data=df_exp)
                st.write("**Civic Action ANOVA Results**")
                st.dataframe(aov2, use_container_width=True)
            except Exception as e:
                st.error(f"ANOVA error: {e}")