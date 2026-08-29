from polyquant.market_graph import MarketGraph
from polyquant.models import Market


def test_subset_threshold_anomaly():
    low=Market(id="low",question="Will Bitcoin reach $150k before year end?",yes_price=.42)
    high=Market(id="high",question="Will Bitcoin reach $200k before year end?",yes_price=.48)
    anomalies=MarketGraph().anomalies([low,high])
    assert anomalies
    assert anomalies[0].left_market_id == "high"
    assert anomalies[0].right_market_id == "low"
