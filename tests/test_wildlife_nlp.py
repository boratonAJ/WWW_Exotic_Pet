"""Tests for wildlife NLP utilities."""

from src.wildlife_nlp import extract_wildlife_entities, predict_conservation_risk


def test_extract_wildlife_entities_identifies_wildlife_terms():
    texts = [
        "Illegal wildlife trade harms biodiversity and public safety.",
        "Cute monkey for sale.",
    ]

    entities = extract_wildlife_entities(texts)

    assert not entities.empty
    assert set(entities["label"]).issuperset({"LEGAL", "CONSERVATION", "TRADE", "SPECIES"})
    assert "monkey" in entities["entity"].tolist()


def test_predict_conservation_risk_returns_labels():
    texts = [
        "Illegal wildlife trafficking of endangered species should be stopped immediately.",
        "Cute monkey for sale.",
    ]

    risk_df = predict_conservation_risk(texts)

    assert len(risk_df) == 2
    assert set(risk_df.columns).issuperset({"text", "risk_score", "risk_label", "matched_terms"})
    assert risk_df.loc[0, "risk_label"] == "high"
    assert risk_df.loc[1, "risk_label"] == "low"
