from polyquant.config import Settings
from polyquant.demo_data import DEMO_MARKETS, demo_book
from polyquant.features import FeatureEngine
from polyquant.models import Prediction
from polyquant.risk import RiskEngine, fractional_kelly

def test_kelly_nonnegative(): assert fractional_kelly(.65,.5,.25) > 0

def test_risk_rejects_large_order():
    s=Settings(); m=DEMO_MARKETS[0]; f=FeatureEngine().compute(m,demo_book(m))
    p=Prediction(market_id=m.id,market_probability=.43,raw_probability=.55,model_probability=.55,confidence=.8,edge=.12,direction='YES')
    d=RiskEngine(s).evaluate(p,f,10_000,0,1000)
    assert not d.approved
    assert d.max_notional == 300
