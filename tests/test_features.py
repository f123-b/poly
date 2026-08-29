from polyquant.demo_data import DEMO_MARKETS, demo_book
from polyquant.features import FeatureEngine

def test_feature_ranges():
    m=DEMO_MARKETS[0]; f=FeatureEngine().compute(m,demo_book(m))
    assert 0 <= f.opportunity_score <= 100
    assert -1 <= f.orderbook_imbalance <= 1
    assert f.best_ask > f.best_bid
