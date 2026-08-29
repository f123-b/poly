import pytest
from types import SimpleNamespace
from polyquant.auto_trader import AutoTrader
from polyquant.models import FeatureSnapshot,Market,Opportunity,Prediction
from polyquant.portfolio import PaperBroker

class FakeService:
    def __init__(self):
        self.s=SimpleNamespace(scan_limit=12);self.broker=PaperBroker(1000,slippage_bps=0);self.calls=0
        m=Market(id='m',question='Q',yes_price=.4,no_price=.6,source='demo');f=FeatureSnapshot(market_id='m',market_probability=.4,liquidity=10000);p=Prediction(market_id='m',market_probability=.4,raw_probability=.6,model_probability=.55,confidence=.8,edge=.15,direction='YES');self.op=Opportunity(market=m,features=f,prediction=p)
    async def opportunities(self,n):return [self.op]
    async def paper_order(self,req):
        self.calls+=1;t=self.broker.execute('m','YES','BUY',req.notional,.4);return SimpleNamespace(approved=True,reasons=[]),t

@pytest.mark.asyncio
async def test_auto_trader_skips_existing_position_without_pyramiding():
    s=FakeService();a=AutoTrader(s,60,20,3,False);r1=await a.run_once();r2=await a.run_once();assert r1['executed']==1 and r2['executed']==1 and r2['skipped']==1 and s.calls==1
