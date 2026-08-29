from __future__ import annotations
import asyncio
import json
from datetime import datetime, timezone
from .calibration import calibration_metrics
from .config import Settings
from .demo_data import DEMO_MARKETS, demo_book
from .event_intelligence import EventIntelligence
from .features import FeatureEngine
from .market_graph import MarketGraph
from .models import Market, Opportunity, OrderBook, PaperOrderRequest, LiveOrderRequest, RiskDecision
from .polymarket import PolymarketDataClient
from .portfolio import PaperBroker
from .probability import ProbabilityEngine
from .risk import RiskEngine
from .storage import Storage
from .live_execution import PolymarketLiveExecutor, REQUEST_CONFIRMATION

class QuantService:
    def __init__(self,settings:Settings):
        self.s=settings; self.client=PolymarketDataClient(); self.features=FeatureEngine(); self.prob=ProbabilityEngine(settings); self.risk=RiskEngine(settings)
        self.broker=PaperBroker(settings.starting_cash); self.storage=Storage(settings.db_path); self.live=PolymarketLiveExecutor(settings); self.events=EventIntelligence(settings.event_feed_url); self.graph=MarketGraph(); self._markets:dict[str,Market]={}; self.last_source="demo"
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
    async def market_evidence(self,market_id:str):
        if market_id not in self._markets: await self.markets()
        market=self._markets.get(market_id)
        if not market: raise KeyError(market_id)
        evidence=await self.events.for_market(market)
        self.storage.save_evidence(market_id,evidence.model_dump_json())
        return evidence
    async def event_feed(self):
        return await self.events.fetch()
    async def graph_anomalies(self):
        return self.graph.anomalies(await self.markets())
    def resolve(self,market_id:str,outcome:str):
        self.storage.save_resolution(market_id,1 if outcome=="YES" else 0)
        return {"market_id":market_id,"outcome":outcome,"saved":True}
    def historical_calibration(self):
        probs,outcomes=self.storage.calibration_pairs()
        if not probs:
            return {"sample_size":0,"brier":None,"log_loss":None,"ece":None,"bins":[]}
        result=calibration_metrics(probs,outcomes,bins=10)
        result["sample_size"]=len(probs)
        return result
    async def paper_order(self,req:PaperOrderRequest):
        op=await self.get_market(req.market_id); acc=self.broker.account()
        ref=op.market.yes_price if req.outcome=="YES" else op.market.no_price
        if req.side == "SELL":
            pos=next((p for p in acc.positions if p.market_id==req.market_id and p.outcome==req.outcome),None)
            max_exit=(pos.shares*ref) if pos else 0.0
            if req.notional > max_exit + 1e-9:
                return RiskDecision(approved=False,reasons=[f"卖出金额超过现有持仓市值 ${max_exit:.2f}"],max_notional=max_exit,suggested_notional=max_exit),None
            decision=RiskDecision(approved=True,reasons=["风险降低型退出"],max_notional=max_exit,suggested_notional=req.notional)
        else:
            pred=op.prediction
            if pred.direction != req.outcome: pred=pred.model_copy(update={"direction":"PASS"})
            decision=self.risk.evaluate(pred,op.features,acc.equity,acc.exposure,req.notional,self.broker.market_exposure(req.market_id))
            if not decision.approved: return decision,None
        trade=self.broker.execute(req.market_id,req.outcome,req.side,req.notional,ref); self.storage.save_trade(trade)
        return decision,trade
    async def live_order(self, req:LiveOrderRequest):
        if req.confirmation != REQUEST_CONFIRMATION:
            return RiskDecision(approved=False,reasons=[f"confirmation must equal {REQUEST_CONFIRMATION}"]),None
        op=await self.get_market(req.market_id); p=op.prediction; f=op.features; reasons=[]
        if op.market.source != "polymarket": reasons.append("Live execution only accepts real Polymarket markets")
        if p.direction != req.outcome or p.direction == "PASS": reasons.append("当前模型方向与请求不一致或无可交易 Edge")
        if p.edge < self.s.min_edge: reasons.append(f"Edge {p.edge:.1%} < {self.s.min_edge:.1%}")
        if p.confidence < self.s.min_confidence: reasons.append(f"Confidence {p.confidence:.1%} < {self.s.min_confidence:.1%}")
        if f.spread > self.s.max_spread: reasons.append(f"Spread {f.spread:.1%} > {self.s.max_spread:.1%}")
        if f.liquidity < self.s.min_liquidity: reasons.append(f"Liquidity ${f.liquidity:,.0f} < ${self.s.min_liquidity:,.0f}")
        if req.notional > self.s.live_max_order_notional: reasons.append(f"实盘单笔上限 ${self.s.live_max_order_notional:.2f}")
        day=datetime.now(timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0).isoformat(); daily=self.storage.live_notional_since(day); market_used=self.storage.live_notional_since(day,req.market_id)
        if daily+req.notional > self.s.live_max_daily_notional: reasons.append(f"实盘日累计上限 ${self.s.live_max_daily_notional:.2f}")
        if market_used+req.notional > self.s.live_max_market_notional: reasons.append(f"单市场实盘累计上限 ${self.s.live_max_market_notional:.2f}")
        token=op.market.yes_token_id if req.outcome=="YES" else op.market.no_token_id
        if not token: reasons.append("市场缺少可交易 token id")
        preflight=await self.live.preflight(); reasons.extend(preflight["reasons"])
        if reasons: return RiskDecision(approved=False,reasons=list(dict.fromkeys(reasons)),max_notional=min(self.s.live_max_order_notional,max(0,self.s.live_max_daily_notional-daily))),None
        result=await self.live.place_market_buy(token,req.notional); self.storage.save_live_trade(req.market_id,req.notional,result["submitted_at"],json.dumps(result,ensure_ascii=False))
        return RiskDecision(approved=True,reasons=["通过实盘硬门禁"],max_notional=self.s.live_max_order_notional,suggested_notional=req.notional),result
