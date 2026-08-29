from polyquant.demo_data import DEMO_MARKETS
from polyquant.strategies import CrossMarketAnalyzer

def test_cross_market_anomaly_demo():
    rows=CrossMarketAnalyzer().find(DEMO_MARKETS)
    assert any(x.lower_market_id=='demo-btc' and x.upper_market_id=='demo-btc200' for x in rows)
