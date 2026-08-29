from __future__ import annotations
import asyncio,json
from datetime import datetime,timezone
from .analytics import ModelAnalytics
from .calibration import calibration_metrics
from .config import Settings
from .demo_data import DEMO_MARKETS,demo_book
from .event_intelligence import EventIntelligence,MarketEvidence
from .features import FeatureEngine
from .market_graph import MarketGraph
from .models import LiveOrderRequest,Market,Opportunity,OrderBook,PaperOrderRequest,RiskDecision
from .polymarket import PolymarketDataClient
from .portfolio import PaperBroker
from .probability import ProbabilityEngine
from .risk import RiskEngine
from .smart_money import SmartMoneyClient
from .storage import Storage
from .live_execution import PolymarketLiveExecutor,REQUEST_CONFIRMATION

class QuantService:
    def __init__(self,settings:Settings):
        self.s=settings;self.client=PolymarketDataClient();self.features=FeatureEngine();self.prob=ProbabilityEngine(settings);self.risk=RiskEngine(settings);self.storage=Storage(settings.db_path);starting=self.storage.paper_starting_cash(settings.starting_cash);self.broker=PaperBroker(starting,settings.paper_fee_bps,settings.paper_slippage_bps);self.broker.restore(self.storage.paper_trades(),self.storage.latest_marks(),self.storage.paper_settlements());self.live=PolymarketLiveExecutor(settings);self.events=EventIntelligence(settings.event_feed_url);self.graph=MarketGraph();self.smart=SmartMoneyClient(demo=settings.mode=='demo' or settings.smart_money_demo);self.analytics=ModelAnalytics();self._markets={};self.last_source='demo';self.realtime_cache=None
        for r in self.storage.resolution_rows():
            if self.broker.market_exposure(r['market_id'])>0 and not self.storage.settlement_exists(r['market_id']):self.storage.save_settlement(self.broker.settle(r['market_id'],r['outcome']))
    def _live_market(self,m:Market)->Market:
        cache=getattr(self,'realtime_cache',None)
        if cache is None:return m
        try:prices=cache.market_prices(m)
        except Exception:prices=None
        return m.model_copy(update={'yes_price':prices['yes_price'],'no_price':prices['no_price']}) if prices else m
    async def markets(self)->list[Market]:
        data=[]
        if self.s.mode!='demo':
            try:data=await self.client.list_markets(self.s.scan_limit)
            except Exception:data=[]
        if not data:data=DEMO_MARKETS[:self.s.scan_limit];self.last_source='demo'
        else:self.last_source='polymarket'
        data=[self._live_market(m) for m in data];self._markets={m.id:m for m in data}
        for m in data:self.storage.save_market_snapshot(m);self.broker.mark(m.id,'YES',m.yes_price);self.broker.mark(m.id,'NO',m.no_price)
        return data
    async def _book(self,m:Market)->OrderBook:
        cache=getattr(self,'realtime_cache',None)
        if cache is not None and m.yes_token_id:
            try:
                book=cache.book(m.yes_token_id)
                if book is not None:return book
            except Exception:pass
        if m.source=='polymarket' and m.yes_token_id:
            try:return await self.client.get_order_book(m.yes_token_id)
            except Exception:pass
        return demo_book(m)
    async def opportunity_for(self,m:Market,evidence:MarketEvidence|None=None)->Opportunity:
        m=self._live_market(m);book=await self._book(m);f=self.features.compute(m,book);self.storage.save_feature_snapshot(f)
        if evidence is None:
            try:evidence=await self.events.for_market(m)
            except Exception:evidence=MarketEvidence(market_id=m.id)
        self.storage.save_evidence(m.id,evidence.model_dump_json());p=await self.prob.predict(m,f,evidence);pid=self.storage.save_prediction(p);self.broker.mark(m.id,'YES',m.yes_price);self.broker.mark(m.id,'NO',m.no_price);return Opportunity(market=m,features=f,prediction=p,prediction_id=pid)
    async def opportunities(self,limit:int=12)->list[Opportunity]:
        ms=await self.markets();sem=asyncio.Semaphore(6)
        try:items=await self.events.fetch()
        except Exception:items=[]
        async def one(m):
            async with sem:
                evidence=await self.events.for_market(m,items=items) if items else MarketEvidence(market_id=m.id);return await self.opportunity_for(m,evidence)
        ops=await asyncio.gather(*(one(m) for m in ms[:max(limit,1)]));return sorted(ops,key=lambda x:(x.prediction.edge,x.features.opportunity_score),reverse=True)
    async def get_market(self,market_id:str)->Opportunity:
        if market_id not in self._markets:await self.markets()
        m=self._markets.get(market_id)
        if not m:raise KeyError(market_id)
        return await self.opportunity_for(m)
    async def market_evidence(self,market_id:str):
        if market_id not in self._markets:await self.markets()
        market=self._markets.get(market_id)
        if not market:raise KeyError(market_id)
        evidence=await self.events.for_market(market);self.storage.save_evidence(market_id,evidence.model_dump_json());return evidence
    async def event_feed(self):return await self.events.fetch()
    async def graph_anomalies(self):return self.graph.anomalies(await self.markets())
    async def market_history(self,market_id:str,limit:int|None=None):
        if market_id not in self._markets:await self.markets()
        market=self._markets.get(market_id)
        if not market:raise KeyError(market_id)
        local=self.storage.market_history(market_id,limit or self.s.history_limit);remote=[]
        if market.source=='polymarket' and market.yes_token_id:
            try:remote=[{'timestamp':t,'yes_price':p} for t,p in await self.client.price_history(market.yes_token_id,'1d',60)]
            except Exception:remote=[]
        return {'market_id':market_id,'source':'polymarket-history' if remote else 'local-snapshots','points':remote or local}
    def research_history(self,market_id,limit=100):return self.storage.research_history(market_id,limit)
    def scorecards(self):return self.analytics.scorecards(self.storage.scorecard_rows())
    def prediction_dataset(self,limit=10000):return self.storage.prediction_dataset(limit)
    async def trader_profile(self,wallet):
        profile=await self.smart.profile(wallet);self.storage.save_trader_profile(profile['wallet'],profile);return profile
    async def smart_money_flow(self,market_id):
        if market_id not in self._markets:await self.markets()
        market=self._markets.get(market_id)
        if not market:raise KeyError(market_id)
        if market.source=='demo':return await self.smart.market_flow(market.condition_id or market.id)
        if not market.condition_id:return {'market_id':market_id,'score':0.0,'reason':'condition_id unavailable'}
        result=await self.smart.market_flow(market.condition_id);return {'market_id':market_id,**result}
    def _record_resolution(self,market_id,outcome):
        self.storage.save_resolution(market_id,1 if outcome=='YES' else 0);settlement=None
        if self.broker.market_exposure(market_id)>0 and not self.storage.settlement_exists(market_id):settlement=self.broker.settle(market_id,outcome);self.storage.save_settlement(settlement)
        return {'market_id':market_id,'outcome':outcome,'saved':True,'paper_settlement':settlement.model_dump() if settlement else None}
    def resolve(self,market_id,outcome):return self._record_resolution(market_id,outcome)
    async def sync_resolutions(self,limit=100):
        if self.s.mode=='demo':return {'source':'demo','scanned':0,'saved':0,'note':'Resolution sync is disabled in offline demo mode.'}
        rows=await self.client.list_resolved_markets(limit);settled=0
        for m,outcome in rows:
            r=self._record_resolution(m.id,outcome);settled+=1 if r['paper_settlement'] else 0
        return {'source':'polymarket','scanned':len(rows),'saved':len(rows),'paper_settlements':settled,'calibration':self.historical_calibration()}
    def historical_calibration(self):
        probs,outcomes=self.storage.calibration_pairs()
        if not probs:return {'samples':0,'brier_score':None,'log_loss':None,'ece':None,'bins':[]}
        return calibration_metrics(probs,outcomes,bins=10).model_dump()
    def system_status(self):
        acc=self.broker.account();w=self.storage.stats();cache=getattr(self,'realtime_cache',None);return {'version':'8.0.0','data_source':self.last_source,'warehouse':w,'paper':{'persistent':True,'starting_cash':acc.starting_cash,'equity':acc.equity,'cash':acc.cash,'exposure':acc.exposure,'positions':len(acc.positions),'trades_total':w['paper_trades'],'settlements':w['paper_settlements']},'audit':{'decisions':w['decision_audit']},'quant_data':{'realtime_cache_attached':cache is not None,'realtime_books':cache.snapshot()['books'] if cache is not None else 0},'risk':{'min_edge':self.s.min_edge,'min_confidence':self.s.min_confidence,'max_spread':self.s.max_spread,'min_liquidity':self.s.min_liquidity,'max_single_market_pct':self.s.max_single_market_pct,'max_total_exposure_pct':self.s.max_total_exposure_pct,'fractional_kelly':self.s.fractional_kelly},'live_execution_enabled':self.s.live_execution_enabled,'auto_execution':'paper-only','auto_pyramiding':self.s.auto_allow_pyramiding}
    def _audited(self,decision,market_id,prediction_id,mode,action,request,result_id=None):
        did=self.storage.save_decision(market_id,prediction_id,mode,action,request,decision.model_dump(exclude={'decision_id'}),result_id);return decision.model_copy(update={'decision_id':did})
    async def paper_order(self,req:PaperOrderRequest):
        resolved=self.storage.resolution_for(req.market_id)
        if resolved:
            d=RiskDecision(approved=False,reasons=[f"市场已结算为 {resolved['outcome']}，禁止新的 Paper 交易"]);return self._audited(d,req.market_id,None,'paper',f'{req.side}_{req.outcome}',req.model_dump()),None
        op=await self.get_market(req.market_id);acc=self.broker.account();ref=op.market.yes_price if req.outcome=='YES' else op.market.no_price
        if req.side=='SELL':
            pos=next((p for p in acc.positions if p.market_id==req.market_id and p.outcome==req.outcome),None);max_exit=(pos.shares*ref) if pos else 0.0
            if req.notional>max_exit+1e-9:d=RiskDecision(approved=False,reasons=[f'卖出金额超过现有持仓市值 ${max_exit:.2f}'],max_notional=max_exit,suggested_notional=max_exit);return self._audited(d,req.market_id,op.prediction_id,'paper',f'{req.side}_{req.outcome}',req.model_dump()),None
            d=RiskDecision(approved=True,reasons=['风险降低型退出'],max_notional=max_exit,suggested_notional=req.notional)
        else:
            pred=op.prediction
            if pred.direction!=req.outcome:pred=pred.model_copy(update={'direction':'PASS'})
            d=self.risk.evaluate(pred,op.features,acc.equity,acc.exposure,req.notional,self.broker.market_exposure(req.market_id))
            if not d.approved:return self._audited(d,req.market_id,op.prediction_id,'paper',f'{req.side}_{req.outcome}',req.model_dump()),None
        trade=self.broker.execute(req.market_id,req.outcome,req.side,req.notional,ref);self.storage.save_trade(trade);return self._audited(d,req.market_id,op.prediction_id,'paper',f'{req.side}_{req.outcome}',req.model_dump(),trade.id),trade
    async def live_order(self,req:LiveOrderRequest):
        if req.confirmation!=REQUEST_CONFIRMATION:
            d=RiskDecision(approved=False,reasons=[f'confirmation must equal {REQUEST_CONFIRMATION}']);return self._audited(d,req.market_id,None,'live',f'BUY_{req.outcome}',{'market_id':req.market_id,'outcome':req.outcome,'notional':req.notional}),None
        op=await self.get_market(req.market_id);p=op.prediction;f=op.features;reasons=[]
        if op.market.source!='polymarket':reasons.append('Live execution only accepts real Polymarket markets')
        if p.direction!=req.outcome or p.direction=='PASS':reasons.append('当前模型方向与请求不一致或无可交易 Edge')
        if p.edge<self.s.min_edge:reasons.append(f'Edge {p.edge:.1%} < {self.s.min_edge:.1%}')
        if p.confidence<self.s.min_confidence:reasons.append(f'Confidence {p.confidence:.1%} < {self.s.min_confidence:.1%}')
        if f.spread>self.s.max_spread:reasons.append(f'Spread {f.spread:.1%} > {self.s.max_spread:.1%}')
        if f.liquidity<self.s.min_liquidity:reasons.append(f'Liquidity ${f.liquidity:,.0f} < ${self.s.min_liquidity:,.0f}')
        if req.notional>self.s.live_max_order_notional:reasons.append(f'实盘单笔上限 ${self.s.live_max_order_notional:.2f}')
        day=datetime.now(timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0).isoformat();daily=self.storage.live_notional_since(day);market_used=self.storage.live_notional_since(day,req.market_id)
        if daily+req.notional>self.s.live_max_daily_notional:reasons.append(f'实盘日累计上限 ${self.s.live_max_daily_notional:.2f}')
        if market_used+req.notional>self.s.live_max_market_notional:reasons.append(f'单市场实盘累计上限 ${self.s.live_max_market_notional:.2f}')
        token=op.market.yes_token_id if req.outcome=='YES' else op.market.no_token_id
        if not token:reasons.append('市场缺少可交易 token id')
        preflight=await self.live.preflight();reasons.extend(preflight['reasons']);request={'market_id':req.market_id,'outcome':req.outcome,'notional':req.notional}
        if reasons:
            d=RiskDecision(approved=False,reasons=list(dict.fromkeys(reasons)),max_notional=min(self.s.live_max_order_notional,max(0,self.s.live_max_daily_notional-daily)));return self._audited(d,req.market_id,op.prediction_id,'live',f'BUY_{req.outcome}',request),None
        result=await self.live.place_market_buy(token,req.notional);self.storage.save_live_trade(req.market_id,req.notional,result['submitted_at'],json.dumps(result,ensure_ascii=False));rid=str(result.get('orderID') or result.get('id') or result['submitted_at']);d=RiskDecision(approved=True,reasons=['通过实盘硬门禁'],max_notional=self.s.live_max_order_notional,suggested_notional=req.notional);return self._audited(d,req.market_id,op.prediction_id,'live',f'BUY_{req.outcome}',request,rid),result
