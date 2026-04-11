import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()

def load_and_prepare_data(file):
    df = pd.read_csv(file)

    # Normalize text column
    if "text_content" not in df.columns:
        for col in ["text", "snippet"]:
            if col in df.columns:
                df["text_content"] = df[col]
                break

    df["text_content"] = df["text_content"].fillna("")

    # Sentiment scoring
    df["sentiment_score"] = df["text_content"].apply(
        lambda x: analyzer.polarity_scores(str(x))["compound"]
    )

    df["sentiment_label"] = df["sentiment_score"].apply(label_sentiment)

    return df


def label_sentiment(score):
    if score > 0.05:
        return "Positive"
    elif score < -0.05:
        return "Negative"
    return "Neutral"