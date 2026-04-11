# !/usr/bin/env python3

"""
Research-Grade Text Analytics and Sentiment Analysis Pipeline
------------------------------------------------------------
This script performs:
1. Text preprocessing
2. Text analytics:
   - keyword extraction (TF-IDF)
   - topic modeling (LDA)
   - named entity recognition (spaCy)
3. Sentiment analysis using VADER
4. Summary reporting

Author: Your Name
Use case: Social media comments, reviews, discussion posts, survey responses
"""

# import nltk

# nltk.download("punkt")
# nltk.download("stopwords")
# nltk.download("wordnet")
# nltk.download("omw-1.4")
# nltk.download("vader_lexicon")


from __future__ import annotations

import re
import string
from collections import Counter
from typing import List, Dict, Any

import numpy as np
import pandas as pd

import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import word_tokenize

import spacy
from spacy.cli import download as spacy_download
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation


# =========================
# 1. DOWNLOAD RESOURCES
# =========================
def download_nlp_resources() -> None:
    """Download required NLTK resources."""
    resources = [
        "punkt",
        "stopwords",
        "wordnet",
        "omw-1.4",
        "vader_lexicon",
    ]
    for resource in resources:
        nltk.download(resource, quiet=True)


# =========================
# 2. TEXT PREPROCESSING
# =========================
class TextPreprocessor:
    """Preprocess text for analytics tasks."""

    def __init__(self) -> None:
        self.stop_words = set(stopwords.words("english"))
        self.lemmatizer = WordNetLemmatizer()

    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean raw text by:
        - lowering case
        - removing URLs
        - removing mentions/hashtags symbols
        - removing punctuation
        - removing extra whitespace
        """
        if pd.isna(text):
            return ""

        text = str(text).lower()
        text = re.sub(r"http\S+|www\S+|https\S+", "", text)
        text = re.sub(r"@\w+", "", text)
        text = re.sub(r"#", "", text)
        text = re.sub(r"\d+", "", text)
        text = text.translate(str.maketrans("", "", string.punctuation))
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def tokenize_and_lemmatize(self, text: str) -> List[str]:
        """Tokenize, remove stopwords, and lemmatize."""
        tokens = word_tokenize(text)
        processed = [
            self.lemmatizer.lemmatize(token)
            for token in tokens
            if token.isalpha() and token not in self.stop_words and len(token) > 2
        ]
        return processed

    def preprocess(self, text: str) -> str:
        """Full preprocessing pipeline returning cleaned string."""
        cleaned = self.clean_text(text)
        tokens = self.tokenize_and_lemmatize(cleaned)
        return " ".join(tokens)


# =========================
# 3. SENTIMENT ANALYSIS
# =========================
class SentimentAnalyzer:
    """Sentiment analysis using NLTK VADER."""

    def __init__(self) -> None:
        self.analyzer = SentimentIntensityAnalyzer()

    def score_sentiment(self, text: str) -> Dict[str, float]:
        """Return VADER sentiment scores."""
        if not text:
            return {
                "neg": 0.0,
                "neu": 0.0,
                "pos": 0.0,
                "compound": 0.0,
            }
        return self.analyzer.polarity_scores(text)

    @staticmethod
    def label_sentiment(compound: float) -> str:
        """
        Convert compound score into sentiment label.
        Standard VADER thresholds:
        - compound >= 0.05  : positive
        - compound <= -0.05 : negative
        - otherwise         : neutral
        """
        if compound >= 0.05:
            return "positive"
        elif compound <= -0.05:
            return "negative"
        return "neutral"


# =========================
# 4. TEXT ANALYTICS
# =========================
class TextAnalytics:
    """Text analytics methods: keywords, topics, entities."""

    def __init__(self, spacy_model: str = "en_core_web_sm") -> None:
        try:
            self.nlp = spacy.load(spacy_model)
        except OSError:
            print(f"Downloading spaCy model: {spacy_model}...")
            spacy_download(spacy_model)
            self.nlp = spacy.load(spacy_model)

    def extract_top_keywords_tfidf(
        self,
        texts: List[str],
        top_n: int = 20,
        max_features: int = 1000,
    ) -> pd.DataFrame:
        """Extract top keywords across the corpus using TF-IDF."""
        vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=(1, 2),
            stop_words="english"
        )
        tfidf_matrix = vectorizer.fit_transform(texts)

        feature_names = np.array(vectorizer.get_feature_names_out())
        mean_scores = np.asarray(tfidf_matrix.mean(axis=0)).ravel()

        top_indices = mean_scores.argsort()[::-1][:top_n]

        keywords_df = pd.DataFrame({
            "keyword": feature_names[top_indices],
            "tfidf_score": mean_scores[top_indices]
        })

        return keywords_df

    def topic_modeling_lda(
        self,
        texts: List[str],
        n_topics: int = 5,
        n_top_words: int = 10,
        max_features: int = 1000,
    ) -> pd.DataFrame:
        """Perform topic modeling using LDA."""
        vectorizer = CountVectorizer(
            max_features=max_features,
            stop_words="english"
        )
        doc_term_matrix = vectorizer.fit_transform(texts)

        lda = LatentDirichletAllocation(
            n_components=n_topics,
            random_state=42,
            learning_method="batch"
        )
        lda.fit(doc_term_matrix)

        feature_names = vectorizer.get_feature_names_out()
        topics = []

        for topic_idx, topic in enumerate(lda.components_):
            top_features_idx = topic.argsort()[::-1][:n_top_words]
            top_words = [feature_names[i] for i in top_features_idx]
            topics.append({
                "topic_number": topic_idx + 1,
                "top_words": ", ".join(top_words)
            })

        return pd.DataFrame(topics)

    def extract_named_entities(
        self,
        texts: List[str],
        max_docs: int = 200,
    ) -> pd.DataFrame:
        """
        Extract named entities from text corpus.
        max_docs limits processing for efficiency on large datasets.
        """
        entities = []

        for text in texts[:max_docs]:
            if not text.strip():
                continue
            doc = self.nlp(text)
            for ent in doc.ents:
                entities.append({
                    "entity": ent.text,
                    "label": ent.label_
                })

        if not entities:
            return pd.DataFrame(columns=["entity", "label", "count"])

        entities_df = pd.DataFrame(entities)
        entities_df = (
            entities_df
            .groupby(["entity", "label"])
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
        )
        return entities_df


# =========================
# 5. MAIN PIPELINE
# =========================
def run_text_analytics_pipeline(
    df: pd.DataFrame,
    text_column: str = "text"
) -> Dict[str, Any]:
    """
    Run full text analytics and sentiment pipeline.

    Parameters
    ----------
    df : pd.DataFrame
        Input dataframe containing text data.
    text_column : str
        Name of the column containing raw text.

    Returns
    -------
    dict
        Dictionary containing processed data and results.
    """
    if text_column not in df.columns:
        raise ValueError(f"Column '{text_column}' not found in DataFrame.")

    download_nlp_resources()

    preprocessor = TextPreprocessor()
    sentiment_model = SentimentAnalyzer()
    analytics_model = TextAnalytics()

    data = df.copy()
    data[text_column] = data[text_column].fillna("").astype(str)

    # Preprocessing
    data["clean_text"] = data[text_column].apply(preprocessor.clean_text)
    data["processed_text"] = data["clean_text"].apply(preprocessor.preprocess)

    # Sentiment scores
    sentiment_scores = data["clean_text"].apply(sentiment_model.score_sentiment)
    sentiment_df = pd.DataFrame(sentiment_scores.tolist())

    data = pd.concat([data, sentiment_df], axis=1)
    data["sentiment_label"] = data["compound"].apply(sentiment_model.label_sentiment)

    # Text analytics
    valid_texts = data["processed_text"].loc[data["processed_text"].str.strip() != ""].tolist()

    keywords_df = analytics_model.extract_top_keywords_tfidf(valid_texts, top_n=20)
    topics_df = analytics_model.topic_modeling_lda(valid_texts, n_topics=5, n_top_words=10)
    entities_df = analytics_model.extract_named_entities(data["clean_text"].tolist())

    # Sentiment summary
    sentiment_summary = (
        data["sentiment_label"]
        .value_counts(dropna=False)
        .reset_index()
    )
    sentiment_summary.columns = ["sentiment_label", "count"]

    return {
        "processed_data": data,
        "keywords": keywords_df,
        "topics": topics_df,
        "entities": entities_df,
        "sentiment_summary": sentiment_summary
    }


# =========================
# 6. EXAMPLE USAGE
# =========================
if __name__ == "__main__":
    sample_data = {
        "text": [
            "I absolutely love this exotic bird, it is beautiful and amazing!",
            "Keeping wild animals as pets is cruel and dangerous.",
            "This species is protected under conservation law.",
            "The video is informative and educational.",
            "I do not think people should own endangered animals at home.",
            "What a cute monkey! I want one.",
            "Illegal wildlife trade harms biodiversity and public safety.",
            "This is neutral information about reptiles and habitat."
        ]
    }

    df = pd.DataFrame(sample_data)

    results = run_text_analytics_pipeline(df, text_column="text")

    print("\n=== PROCESSED DATA ===")
    print(results["processed_data"][[
        "text", "processed_text", "neg", "neu", "pos", "compound", "sentiment_label"
    ]])

    print("\n=== TOP KEYWORDS ===")
    print(results["keywords"])

    print("\n=== TOPICS ===")
    print(results["topics"])

    print("\n=== NAMED ENTITIES ===")
    print(results["entities"].head(20))

    print("\n=== SENTIMENT SUMMARY ===")
    print(results["sentiment_summary"])

    # Optional: save outputs
    results["processed_data"].to_csv("processed_text_sentiment_results.csv", index=False)
    results["keywords"].to_csv("top_keywords.csv", index=False)
    results["topics"].to_csv("topics.csv", index=False)
    results["entities"].to_csv("entities.csv", index=False)
    results["sentiment_summary"].to_csv("sentiment_summary.csv", index=False)