import plotly.express as px
from wordcloud import WordCloud
import matplotlib.pyplot as plt


def plot_sentiment_distribution(df):
    counts = df["sentiment_label"].value_counts().reset_index()
    counts.columns = ["Sentiment", "Count"]
    return px.bar(counts, x="Sentiment", y="Count")


def plot_sentiment_by_platform(df):
    return px.box(df, x="platform", y="sentiment_score")


def plot_theme_counts(df):
    themes = ["illegal", "danger", "welfare", "conservation"]

    counts = {
        theme: df["text_content"].str.contains(theme, case=False).sum()
        for theme in themes
    }

    return px.bar(
        x=list(counts.keys()),
        y=list(counts.values()),
        labels={"x": "Theme", "y": "Count"}
    )

def plot_wordcloud(text_series):
    text = " ".join(text_series.astype(str))

    wc = WordCloud(
        background_color="white",
        width=800,
        height=400
    ).generate(text)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")

    return fig