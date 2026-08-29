import pytest
from polyquant.event_intelligence import EventIntelligence, EvidenceItem
from polyquant.models import Market


def test_relevance_prefers_matching_event():
    m=Market(id="m",question="Will Bitcoin reach $150k before year end?",category="Crypto")
    good=EvidenceItem(id="1",title="Bitcoin price volatility near threshold",entities=["BTC"])
    bad=EvidenceItem(id="2",title="Federal Reserve rate decision",entities=["Fed"])
    assert EventIntelligence.relevance(m,good) > EventIntelligence.relevance(m,bad)


@pytest.mark.asyncio
async def test_demo_market_evidence_is_bounded():
    m=Market(id="m",question="Will Bitcoin reach $150k before year end?",category="Crypto")
    result=await EventIntelligence().for_market(m)
    assert 0 <= result.evidence_score <= 1
    assert -1 <= result.net_sentiment <= 1
