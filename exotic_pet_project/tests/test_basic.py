from src.data_processing import label_sentiment
from src.wildlife_nlp import predict_risk

def test_sentiment():
    assert label_sentiment(0.6) == "Positive"
    assert label_sentiment(-0.6) == "Negative"
    assert label_sentiment(0.0) == "Neutral"

def test_risk():
    df = predict_risk(["illegal tiger for sale"])
    assert df.iloc[0]["risk_label"] == "high"