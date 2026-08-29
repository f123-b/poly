from __future__ import annotations
import httpx
DATA='https://data-api.polymarket.com'

class SmartMoneyClient:
    def __init__(self,timeout:float=8.0): self.timeout=timeout
    @staticmethod
    def _normalize(rows):
        out=[]
        for x in rows:
            pnl=float(x.get('pnl') or 0); vol=float(x.get('vol') or x.get('volume') or 0); wallet=x.get('proxyWallet') or x.get('wallet') or 'unknown'; verified=bool(x.get('verifiedBadge',False)); efficiency=pnl/max(vol,1.0); score=max(0.0,min(100.0,50+efficiency*250+(8 if verified else 0)))
            out.append({'rank':x.get('rank'),'wallet':wallet,'name':x.get('userName') or x.get('pseudonym') or x.get('name') or 'Anonymous','pnl':pnl,'volume':vol,'verified':verified,'efficiency':efficiency,'trader_score':score})
        return out
    @staticmethod
    def demo():
        return SmartMoneyClient._normalize([{'rank':1,'wallet':'demo-alpha','name':'Demo Alpha','pnl':48200,'vol':410000,'verifiedBadge':True},{'rank':2,'wallet':'demo-beta','name':'Demo Beta','pnl':27100,'vol':330000,'verifiedBadge':False},{'rank':3,'wallet':'demo-gamma','name':'Demo Gamma','pnl':9800,'vol':155000,'verifiedBadge':False}])
    async def leaderboard(self,category:str='OVERALL',time_period:str='MONTH',limit:int=10):
        params={'category':category.upper(),'timePeriod':time_period.upper(),'orderBy':'PNL','limit':min(max(limit,1),50),'offset':0}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r=await client.get(f'{DATA}/v1/leaderboard',params=params); r.raise_for_status(); rows=r.json()
            if not isinstance(rows,list): raise ValueError('leaderboard payload must be list')
            return self._normalize(rows)
        except Exception:
            return self.demo()[:params['limit']]
    async def profiles(self,category:str='OVERALL',time_period:str='MONTH',limit:int=20):
        rows=await self.leaderboard(category,time_period,limit); return {'source':'demo-fallback' if rows and str(rows[0]['wallet']).startswith('demo-') else 'polymarket','degraded':bool(rows and str(rows[0]['wallet']).startswith('demo-')),'profiles':rows}
