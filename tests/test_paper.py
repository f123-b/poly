import asyncio
from pathlib import Path
from polyquant.config import Settings
from polyquant.models import PaperOrderRequest
from polyquant.service import QuantService

def test_paper_trade_full_pipeline(tmp_path:Path):
    svc=QuantService(Settings(mode='demo',db_path=str(tmp_path/'p.db'),scan_limit=5))
    async def run():
        ops=await svc.opportunities(5)
        tradable=next(x for x in ops if x.prediction.direction!='PASS')
        req=PaperOrderRequest(market_id=tradable.market.id,outcome=tradable.prediction.direction,side='BUY',notional=100)
        decision,trade=await svc.paper_order(req)
        return decision,trade,svc.broker.account()
    decision,trade,account=asyncio.run(run())
    assert decision.approved
    assert trade is not None
    assert account.exposure > 0
