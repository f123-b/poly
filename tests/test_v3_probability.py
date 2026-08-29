import asyncio
from polyquant.config import Settings
from polyquant.event_intelligence import EvidenceItem,MarketEvidence
from polyquant.models import FeatureSnapshot,Market
from polyquant.probability import ProbabilityEngine


def test_evidence_adjustment_is_bounded():
    s=Settings(mode='demo',evidence_max_adjustment=.035)
    engine=ProbabilityEngine(s)
    m=Market(id='custom',question='Will Bitcoin test happen?',yes_price=.4,no_price=.6,source='demo')
    f=FeatureSnapshot(market_id=m.id,market_probability=.4,orderbook_imbalance=0,liquidity_score=.8,volume_score=.8)
    e=MarketEvidence(market_id=m.id,evidence=[EvidenceItem(id='e',title='Bitcoin test',reliability=1,sentiment=1)],evidence_score=1,freshness_score=1,net_sentiment=1)
    p=asyncio.run(engine.predict(m,f,e))
    assert abs(p.components['evidence_adjustment'])<=.035+1e-12
    assert p.model_version=='quant-ensemble-v3'
    assert 'calibrated_probability' in p.components
