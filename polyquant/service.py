from __future__ import annotations
import asyncio
from .config import Settings
from .demo_data import DEMO_MARKETS, demo_book
from .features import FeatureEngine
from .models import Market, Opportunity, OrderBook, PaperOrderRequest
from .polymarket import PolymarketDataClient
from .portfolio import PaperBroker
from .probability import ProbabilityEngine
from .risk import RiskEngine
from .storage import Storage

class QuantService:
    def __init__(self,settings:Settings):
        self.s=settings; self.client=PolymarketDataClient(); self.features=FeatureEngine(); self.prob=ProbabilityEngine(settings); self.risk=RiskEngine(settings)
        self.broker=PaperBroker(settings.starting_cash); self.storage=Storage(settings.db_path); self._markets:dict[str,Market]={}; self.last_source="demo"
    async def markets(self)->list[Market]:
        data=[]
        if self.s.mode!="demo":
            try: data=await self.client.list_markets(self.s.scan_limit)
            except Exception: data=[]
        if not data: data=DEMO_MARKETS[:self.s.scan_limit]; self.last_source="demo"
        else: self.last_source="polymarket"
        self._markets={m.id:m for m in data}; return data
    async def _book(self,m:Market)->OrderBook:
        if m.source=="polymarket" and m.yes_token_id:
            try: return await self.client.get_order_book(m.yes_token_id)
            except Exception: pass
        return demo_book(m)
    async def opportunity_for(self,m:Market)->Opportunity:
        book=await self._book(m); f=self.features.compute(m,book); p=await self.prob.predict(m,f); self.storage.save_prediction(p)
        self.broker.mark(m.id,"YES",m.yes_price); self.broker.mark(m.id,"NO",m.no_price)
        return Opportunity(market=m,features=f,prediction=p)
    async def opportunities(self,limit:int=12)->list[Opportunity]:
        ms=await self.markets(); sem=asyncio.Semaphore(6)
        async def one(m):
            async with sem: return await self.opportunity_for(m)
        ops=await asyncio.gather(*(one(m) for m in ms[:max(limit,1)]))
        return sorted(ops,key=lambda x:(x.prediction.edge,x.features.opportunity_score),reverse=True)
    async def get_market(self,market_id:str)->Opportunity:
        if market_id not in self._markets: await self.markets()
        m=self._markets.get(market_id)
        if not m: raise KeyError(market_id)
        return await self.opportunity_for(m)
    async def paper_order(self,req:PaperOrderRequest):
        op=await self.get_market(req.market_id); acc=self.broker.account()
        ref=op.market.yes_price if req.outcome=="YES" else op.market.no_price
        if req.side == "SELL":
            # Risk-reducing exits must remain possible even when the entry signal disappears.
            pos=next((p for p in acc.positions if p.market_id==req.market_id and p.outcome==req.outcome),None)
            max_exit=(pos.shares*ref) if pos else 0.0
            from .models import RiskDecision
            if req.notional > max_exit + 1e-9:
                return RiskDecision(approved=False,reasons=[f"卖出金额超过现有持仓市值 ${max_exit:.2f}"],max_notional=max_exit,suggested_notional=max_exit),None
            decision=RiskDecision(approved=True,reasons=["风险降低型退出"],max_notional=max_exit,suggested_notional=req.notional)
        else:
            pred=op.prediction
            if pred.direction != req.outcome:
                pred=pred.model_copy(update={"direction":"PASS"})
            decision=self.risk.evaluate(pred,op.features,acc.equity,acc.exposure,req.notional,self.broker.market_exposure(req.market_id))
            if not decision.approved: return decision,None
        trade=self.broker.execute(req.market_id,req.outcome,req.side,req.notional,ref); self.storage.save_trade(trade)
        return decision,trade
