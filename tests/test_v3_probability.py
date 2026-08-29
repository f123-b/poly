import asyncio
from polyquant.config import Settings
from polyquant.demo_data import DEMO_MARKETS, demo_book
from polyquant.features import FeatureEngine
from polyquant.event_intelligence import EvidenceItem, MarketEvidence
from polyquant.probability import ProbabilityEngine

def test_evidence_influence_is_bounded():
    m=DEMO_MARKETS[0]; f=FeatureEngine().compute(m,demo_book(m)); s=Settings(mode='demo',evidence_max_influence=.03); engine=ProbabilityEngine(s)
    evidence=MarketEvidence(market_id=m.id,evidence=[EvidenceItem(id='x',title='x',sentiment=1,reliability=1)],evidence_score=1,freshness_score=1,net_sentiment=1)
    with_ev=asyncio.run(engine.predict(m,f,evidence)); without=asyncio.run(engine.predict(m,f,None))
    assert abs(with_ev.raw_probability-without.raw_probability)<=.0300001
    assert with_ev.model_version=='quant-ensemble-v3'
