from __future__ import annotations
import asyncio,re
import httpx

DATA="https://data-api.polymarket.com"; WALLET=re.compile(r"^0x[a-fA-F0-9]{40}$")

def _num(v,default=0.0):
    try:return float(v)
    except (TypeError,ValueError):return default

class SmartMoneyClient:
    def __init__(self,demo:bool=False,timeout:float=10.0):self.demo=demo;self.timeout=timeout
    async def _get(self,path:str,params:dict):
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r=await client.get(f"{DATA}{path}",params=params);r.raise_for_status();return r.json()
    async def leaderboard(self,category:str="OVERALL",time_period:str="MONTH",limit:int=10):
        if self.demo:return self._demo_leaderboard(limit)
        rows=await self._get("/v1/leaderboard",{"category":category.upper(),"timePeriod":time_period.upper(),"orderBy":"PNL","limit":min(max(limit,1),50),"offset":0})
        return [{"rank":x.get("rank"),"wallet":x.get("proxyWallet"),"name":x.get("userName") or x.get("pseudonym") or "Anonymous","pnl":_num(x.get("pnl")),"volume":_num(x.get("vol")),"verified":bool(x.get("verifiedBadge",False))} for x in rows]
    async def profile(self,wallet:str)->dict:
        if self.demo or wallet=="demo":return self._demo_profile(wallet)
        if not WALLET.match(wallet):raise ValueError("invalid wallet address")
        positions,closed,activity,value=await asyncio.gather(
            self._get("/positions",{"user":wallet,"limit":500}),
            self._get("/closed-positions",{"user":wallet,"limit":50,"sortBy":"TIMESTAMP","sortDirection":"DESC"}),
            self._get("/activity",{"user":wallet,"limit":200}),
            self._get("/value",{"user":wallet}),
        )
        closed_pnls=[_num(x.get("realizedPnl")) for x in closed];wins=sum(1 for x in closed_pnls if x>0);losses=sum(1 for x in closed_pnls if x<0);total_closed=len(closed_pnls);gross_volume=sum(_num(x.get("usdcSize"),_num(x.get("size"))*_num(x.get("price"))) for x in activity if str(x.get("type","TRADE")).upper()=="TRADE")
        categories={}
        for x in positions+closed:
            key=str(x.get("eventSlug") or "other").split("-")[0][:24];categories[key]=categories.get(key,0)+abs(_num(x.get("currentValue"),_num(x.get("totalBought"))))
        top_categories=sorted(categories.items(),key=lambda kv:kv[1],reverse=True)[:5]
        position_value=sum(_num(x.get("value")) for x in value) if isinstance(value,list) else _num(value.get("value")) if isinstance(value,dict) else 0.0
        return {"wallet":wallet.lower(),"open_positions":len(positions),"closed_positions":total_closed,"position_value":position_value,"open_cash_pnl":sum(_num(x.get("cashPnl")) for x in positions),"realized_pnl":sum(closed_pnls),"win_rate":wins/max(1,wins+losses),"wins":wins,"losses":losses,"recent_trade_volume":gross_volume,"top_segments":[{"segment":k,"exposure":v} for k,v in top_categories],"sample_activity":len(activity)}
    async def market_flow(self,condition_id:str,leaderboard_size:int=50,trade_limit:int=500)->dict:
        if self.demo or not condition_id:return self._demo_flow(condition_id or "demo")
        leaders,trades=await asyncio.gather(self.leaderboard("OVERALL","ALL",leaderboard_size),self._get("/trades",{"market":condition_id,"limit":min(max(trade_limit,1),10000)}))
        ranks={str(x.get("wallet") or "").lower():x for x in leaders};gross=0.0;net_yes=0.0;matched=0
        for t in trades:
            wallet=str(t.get("proxyWallet") or "").lower()
            if wallet not in ranks:continue
            matched+=1;notional=abs(_num(t.get("size"))*_num(t.get("price")));gross+=notional;outcome=str(t.get("outcome") or "").upper();side=str(t.get("side") or "BUY").upper();sign=1 if outcome=="YES" else -1
            if side=="SELL":sign*=-1
            net_yes+=sign*notional
        score=net_yes/gross if gross else 0.0
        return {"condition_id":condition_id,"smart_trades":matched,"gross_notional":gross,"net_yes_notional":net_yes,"score":max(-1.0,min(1.0,score)),"leaderboard_sample":len(leaders)}
    @staticmethod
    def _demo_leaderboard(limit:int):
        rows=[("0x1111111111111111111111111111111111111111","Atlas",182400,745000),("0x2222222222222222222222222222222222222222","Mosaic",126800,512000),("0x3333333333333333333333333333333333333333","Vector",89300,389000)]
        return [{"rank":i+1,"wallet":w,"name":n,"pnl":p,"volume":v,"verified":i==0} for i,(w,n,p,v) in enumerate(rows[:limit])]
    @staticmethod
    def _demo_profile(wallet:str):
        return {"wallet":wallet,"open_positions":7,"closed_positions":64,"position_value":42800.0,"open_cash_pnl":3150.0,"realized_pnl":28740.0,"win_rate":.625,"wins":40,"losses":24,"recent_trade_volume":184000.0,"top_segments":[{"segment":"politics","exposure":18200.0},{"segment":"crypto","exposure":12700.0}],"sample_activity":96,"demo":True}
    @staticmethod
    def _demo_flow(condition_id:str):
        seed=sum(ord(c) for c in condition_id);score=((seed%41)-20)/100
        return {"condition_id":condition_id,"smart_trades":18,"gross_notional":82400.0,"net_yes_notional":82400.0*score,"score":score,"leaderboard_sample":3,"demo":True}
