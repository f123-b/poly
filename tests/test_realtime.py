import asyncio
from types import SimpleNamespace
import pytest
from polyquant.models import Market
from polyquant.realtime import RealtimeEngine,RealtimeMarketCache

def test_realtime_cache_book_and_quote():
    c=RealtimeMarketCache(20);m=Market(id='m',question='Q',yes_token_id='y',no_token_id='n',source='demo');c.register_markets([m]);q=c.update_book('y',[{'price':.4,'size':10}],[{'price':.42,'size':12}],.41,'test');assert q['best_bid']==.4 and q['best_ask']==.42 and c.book('y').bids[0].size==10

class DemoService:
    def __init__(self):self.s=SimpleNamespace(mode='demo');self.client=None

@pytest.mark.asyncio
async def test_demo_realtime_engine_broadcasts_without_network():
    e=RealtimeEngine(DemoService(),True,True,.5,20,3);q=e.subscribe();await e.start();msg=await asyncio.wait_for(q.get(),2);assert msg['type'] in ('quote','heartbeat');assert e.status()['mode']=='demo-realtime';await e.stop();assert not e.running
