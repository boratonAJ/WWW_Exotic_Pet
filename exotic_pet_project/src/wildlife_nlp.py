import pandas as pd

LEXICONS = {
    "SPECIES": ["tiger", "lion", "monkey", "parrot"],
    "LEGAL": ["illegal", "banned", "permit"],
    "TRADE": ["for sale", "breeder"]
}

def extract_entities(texts):
    results = []

    for i, text in enumerate(texts):
        text = str(text).lower()

        for label, words in LEXICONS.items():
            for w in words:
                if w in text:
                    results.append({
                        "doc_id": i,
                        "entity": w,
                        "label": label
                    })

    return pd.DataFrame(results)

def predict_risk(texts):
    results = []

    for text in texts:
        t = str(text).lower()
        score = 0

        if "illegal" in t:
            score += 4
        if "for sale" in t:
            score += 2
        if "danger" in t:
            score += 2

        label = "low"
        if score >= 6:
            label = "high"
        elif score >= 3:
            label = "medium"

        results.append({
            "text": text,
            "risk_score": score,
            "risk_label": label
        })

    return pd.DataFrame(results)