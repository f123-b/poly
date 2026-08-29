import asyncio
from pathlib import Path
from polyquant.config import Settings
from polyquant.models import PaperOrderRequest
from polyquant.service import QuantService


def test_repeated_orders_cannot_bypass_single_market_cap(tmp_path:Path):
    svc=QuantService(Settings(mode='demo',db_path=str(tmp_path/'r.db'),scan_limit=6))
    async def run():
        ops=await svc.opportunities(6)
        t=next(x for x in ops if x.prediction.direction!='PASS')
        first,_=await svc.paper_order(PaperOrderRequest(market_id=t.market.id,outcome=t.prediction.direction,side='BUY',notional=250))
        second,_=await svc.paper_order(PaperOrderRequest(market_id=t.market.id,outcome=t.prediction.direction,side='BUY',notional=100))
        return first,second,t
    first,second,_=asyncio.run(run())
    assert first.approved
    assert not second.approved


def test_exit_allowed_after_entry(tmp_path:Path):
    svc=QuantService(Settings(mode='demo',db_path=str(tmp_path/'e.db'),scan_limit=6))
    async def run():
        ops=await svc.opportunities(6)
        t=next(x for x in ops if x.prediction.direction!='PASS')
        _,buy=await svc.paper_order(PaperOrderRequest(market_id=t.market.id,outcome=t.prediction.direction,side='BUY',notional=100))
        decision,sell=await svc.paper_order(PaperOrderRequest(market_id=t.market.id,outcome=t.prediction.direction,side='SELL',notional=50))
        return decision,sell
    d,sell=asyncio.run(run())
    assert d.approved and sell is not None
