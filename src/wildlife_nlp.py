"""Wildlife-aware NLP utilities for entity extraction and conservation-risk scoring.

This module provides a lightweight, dependency-friendly alternative to a full
spaCy training pipeline. It uses curated wildlife lexicons for custom NER-style
extraction and a TF-IDF + LogisticRegression classifier with rule-based pseudo
labels for conservation-risk prediction.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split


WILDLIFE_LEXICONS: dict[str, list[str]] = {
    "SPECIES": [
        "tiger",
        "lion",
        "jaguar",
        "cheetah",
        "serval",
        "caracal",
        "ocelot",
        "monkey",
        "macaque",
        "chimpanzee",
        "capuchin",
        "slow loris",
        "lemur",
        "marmoset",
        "pygmy marmoset",
        "kinkajou",
        "parrot",
        "macaw",
        "cockatoo",
        "reptile",
        "python",
        "boa constrictor",
        "monitor lizard",
        "iguana",
        "tortoise",
        "turtle",
        "frog",
        "toad",
        "amphibian",
        "bird",
        "bird of prey",
    ],
    "LEGAL": [
        "illegal",
        "banned",
        "permit",
        "license",
        "licence",
        "regulated",
        "confiscated",
        "seized",
        "law",
        "usda",
        "cites",
        "wildlife trafficking",
        "smuggling",
    ],
    "WELFARE": [
        "cruel",
        "cruelty",
        "suffer",
        "suffering",
        "stress",
        "captivity",
        "neglect",
        "abuse",
        "care",
        "care needs",
        "poor conditions",
        "enrichment",
    ],
    "CONSERVATION": [
        "endangered",
        "extinction",
        "conservation",
        "biodiversity",
        "habitat",
        "poaching",
        "trafficking",
        "invasive",
        "ecosystem",
        "extinct",
        "wildlife",
    ],
    "SAFETY": [
        "danger",
        "dangerous",
        "bite",
        "attack",
        "scratch",
        "venom",
        "injury",
        "hospital",
        "disease",
        "zoonotic",
        "risk",
        "risk to owner",
    ],
    "TRADE": [
        "for sale",
        "selling",
        "available",
        "breeder",
        "expo",
        "shipping",
        "live arrival",
        "contact",
        "dm",
        "pm",
        "whatsapp",
        "telegram",
    ],
}

RISK_WEIGHTS: dict[str, int] = {
    "illegal": 4,
    "banned": 4,
    "permit": 2,
    "license": 2,
    "licensed": 2,
    "regulated": 2,
    "confiscated": 3,
    "seized": 3,
    "wildlife trafficking": 4,
    "smuggling": 4,
    "endangered": 3,
    "extinction": 3,
    "conservation": 2,
    "biodiversity": 2,
    "poaching": 3,
    "invasive": 2,
    "ecosystem": 2,
    "cruel": 2,
    "cruelty": 2,
    "suffer": 2,
    "suffering": 2,
    "stress": 2,
    "captivity": 2,
    "neglect": 2,
    "abuse": 3,
    "care": 1,
    "danger": 2,
    "dangerous": 2,
    "bite": 2,
    "attack": 2,
    "venom": 2,
    "injury": 2,
    "disease": 2,
    "zoonotic": 3,
    "for sale": 1,
    "selling": 1,
    "breeder": 1,
    "shipping": 1,
    "live arrival": 2,
    "whatsapp": 2,
    "telegram": 2,
    "dm": 1,
    "pm": 1,
}


@dataclass
class ConservationRiskClassifier:
    """Container for a trained classifier or rule-based fallback."""

    vectorizer: TfidfVectorizer | None
    model: LogisticRegression | None
    classes_: list[str]
    mode: str
    accuracy: float | None = None



def _normalize_text(text: str) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text).lower()).strip()



def _make_pattern(term: str) -> re.Pattern[str]:
    escaped = re.escape(term.lower())
    escaped = escaped.replace(r"\ ", r"\s+")
    return re.compile(rf"(?<!\w){escaped}(?!\w)", re.IGNORECASE)



def extract_wildlife_entities(texts: Iterable[str], lexicons: dict[str, list[str]] | None = None) -> pd.DataFrame:
    """Extract wildlife-aware entities from a corpus using curated lexicons."""
    lexicons = lexicons or WILDLIFE_LEXICONS
    matches: list[dict[str, str | int]] = []

    for idx, text in enumerate(texts):
        normalized = _normalize_text(text)
        if not normalized:
            continue

        for label, terms in lexicons.items():
            for term in terms:
                pattern = _make_pattern(term)
                for found in pattern.finditer(normalized):
                    matches.append(
                        {
                            "doc_id": idx,
                            "entity": found.group(0),
                            "label": label,
                            "start": found.start(),
                            "end": found.end(),
                        }
                    )

    if not matches:
        return pd.DataFrame(columns=["doc_id", "entity", "label", "start", "end", "count"])

    entities = pd.DataFrame(matches)
    entities["entity"] = entities["entity"].str.lower()

    summary = (
        entities.groupby(["entity", "label"])
        .agg(count=("entity", "size"), example_docs=("doc_id", lambda values: ", ".join(map(str, sorted(set(values))[:5]))))
        .reset_index()
        .sort_values(["count", "entity"], ascending=[False, True])
    )
    return summary



def score_conservation_risk(text: str) -> tuple[float, str, list[str]]:
    """Rule-based conservation-risk score with an interpretable label."""
    normalized = _normalize_text(text)
    if not normalized:
        return 0.0, "low", []

    matched_terms: list[str] = []
    score = 0.0
    for term, weight in RISK_WEIGHTS.items():
        if _make_pattern(term).search(normalized):
            matched_terms.append(term)
            score += weight

    if score >= 8:
        label = "high"
    elif score >= 4:
        label = "medium"
    else:
        label = "low"

    return float(score), label, matched_terms



def _pseudo_label(score: float) -> str:
    if score >= 8:
        return "high"
    if score >= 4:
        return "medium"
    return "low"



def train_conservation_risk_classifier(texts: Iterable[str]) -> ConservationRiskClassifier:
    """Train a small TF-IDF + LogisticRegression risk classifier using pseudo-labels."""
    corpus = [_normalize_text(text) for text in texts if _normalize_text(text)]
    if len(corpus) < 8:
        return ConservationRiskClassifier(vectorizer=None, model=None, classes_=["low", "medium", "high"], mode="rule")

    scores = [score_conservation_risk(text)[0] for text in corpus]
    labels = [_pseudo_label(score) for score in scores]
    unique_labels = sorted(set(labels))

    if len(unique_labels) < 2:
        return ConservationRiskClassifier(vectorizer=None, model=None, classes_=["low", "medium", "high"], mode="rule")

    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=2000)
    X = vectorizer.fit_transform(corpus)
    y = np.array(labels)

    if len(corpus) >= 20 and len(unique_labels) >= 2:
        stratify = y if min(np.bincount(pd.Series(y).astype("category").cat.codes)) > 1 else None
        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.25, random_state=42, stratify=stratify
            )
        except ValueError:
            X_train, X_test, y_train, y_test = X, X, y, y
    else:
        X_train, X_test, y_train, y_test = X, X, y, y

    model = LogisticRegression(max_iter=1000)
    model.fit(X_train, y_train)
    accuracy = float(model.score(X_test, y_test)) if len(y_test) else None

    return ConservationRiskClassifier(
        vectorizer=vectorizer,
        model=model,
        classes_=sorted(unique_labels),
        mode="model",
        accuracy=accuracy,
    )



def predict_conservation_risk(texts: Iterable[str], classifier: ConservationRiskClassifier | None = None) -> pd.DataFrame:
    """Predict conservation risk for texts using a trained model or rule-based fallback."""
    records: list[dict[str, object]] = []
    corpus = list(texts)

    if classifier is None:
        classifier = train_conservation_risk_classifier(corpus)

    if classifier.mode == "model" and classifier.vectorizer is not None and classifier.model is not None:
        clean = [_normalize_text(text) for text in corpus]
        X = classifier.vectorizer.transform(clean)
        predicted = classifier.model.predict(X)
        if hasattr(classifier.model, "predict_proba"):
            proba = classifier.model.predict_proba(X)
            proba_max = proba.max(axis=1)
        else:
            proba_max = np.full(len(corpus), np.nan)

        for text, label, confidence in zip(corpus, predicted, proba_max):
            score, rule_label, matched_terms = score_conservation_risk(text)
            records.append(
                {
                    "text": text,
                    "risk_score": score,
                    "risk_label": str(label),
                    "risk_confidence": float(confidence) if confidence is not None else np.nan,
                    "risk_mode": classifier.mode,
                    "rule_label": rule_label,
                    "matched_terms": ", ".join(matched_terms),
                }
            )
    else:
        for text in corpus:
            score, label, matched_terms = score_conservation_risk(text)
            records.append(
                {
                    "text": text,
                    "risk_score": score,
                    "risk_label": label,
                    "risk_confidence": np.nan,
                    "risk_mode": "rule",
                    "rule_label": label,
                    "matched_terms": ", ".join(matched_terms),
                }
            )

    return pd.DataFrame(records)
