from __future__ import annotations
import httpx

DATA='https://data-api.polymarket.com'

class SmartMoneyClient:
    async def leaderboard(self,category:str='OVERALL',time_period:str='MONTH',limit:int=10):
        params={'category':category.upper(),'timePeriod':time_period.upper(),'orderBy':'PNL','limit':min(max(limit,1),50),'offset':0}
        async with httpx.AsyncClient(timeout=8.0) as client:
            r=await client.get(f'{DATA}/v1/leaderboard',params=params); r.raise_for_status(); rows=r.json()
        return [{'rank':x.get('rank'),'wallet':x.get('proxyWallet'),'name':x.get('userName') or x.get('pseudonym') or 'Anonymous','pnl':float(x.get('pnl') or 0),'volume':float(x.get('vol') or 0),'verified':bool(x.get('verifiedBadge',False))} for x in rows]
