from __future__ import annotations
import asyncio
from datetime import datetime,timezone
from typing import Any
from .demo_data import DEMO_MARKETS
from .models import BookLevel,Market,OrderBook

class RealtimeMarketCache:
    """In-memory read-only quote/book cache. It never calls an executor."""
    def __init__(self,stale_seconds:float=20.0):
        self.stale_seconds=max(1.0,float(stale_seconds));self._token_meta={};self._quotes={};self._books={};self.events=0;self.last_event_at=None
    def register_markets(self,markets:list[Market]):
        for m in markets:
            if m.yes_token_id:
                self._token_meta[m.yes_token_id]=(m.id,'YES');self.update_quote(m.yes_token_id,last_price=m.yes_price,source=m.source)
            if m.no_token_id:
                self._token_meta[m.no_token_id]=(m.id,'NO');self.update_quote(m.no_token_id,last_price=m.no_price,source=m.source)
    def update_quote(self,token_id:str,best_bid:float|None=None,best_ask:float|None=None,last_price:float|None=None,source:str='realtime'):
        old=self._quotes.get(token_id,{})
        q={'token_id':token_id,'market_id':self._token_meta.get(token_id,(None,None))[0],'outcome':self._token_meta.get(token_id,(None,None))[1],'best_bid':best_bid if best_bid is not None else old.get('best_bid'),'best_ask':best_ask if best_ask is not None else old.get('best_ask'),'last_price':last_price if last_price is not None else old.get('last_price'),'source':source,'updated_at':datetime.now(timezone.utc).isoformat()}
        self._quotes[token_id]=q;self.events+=1;self.last_event_at=q['updated_at'];return q
    @staticmethod
    def _value(row,key,index):
        if isinstance(row,dict):return row.get(key)
        if isinstance(row,(list,tuple)):return row[index] if len(row)>index else None
        return getattr(row,key,None)
    @classmethod
    def _levels(cls,rows)->list[BookLevel]:
        out=[]
        for r in rows or []:
            try:out.append(BookLevel(price=float(cls._value(r,'price',0)),size=float(cls._value(r,'size',1))))
            except (TypeError,ValueError):continue
        return out
    def update_book(self,token_id:str,bids,asks,last_price:float|None=None,source:str='realtime'):
        b=self._levels(bids);a=self._levels(asks);book=OrderBook(token_id=token_id,bids=b,asks=a);self._books[token_id]=(book,datetime.now(timezone.utc));return self.update_quote(token_id,best_bid=max((x.price for x in b),default=None),best_ask=min((x.price for x in a),default=None),last_price=last_price,source=source)
    def apply_sdk_event(self,event:Any)->list[dict]:
        typ=getattr(event,'type',None);payload=getattr(event,'payload',None);updates=[]
        if payload is None:return updates
        if typ=='book':
            token=str(payload.token_id);updates.append(self.update_book(token,payload.bids,payload.asks,float(payload.last_trade_price) if payload.last_trade_price is not None else None,'polymarket-wss'))
        elif typ=='best_bid_ask':updates.append(self.update_quote(str(payload.token_id),float(payload.best_bid) if payload.best_bid is not None else None,float(payload.best_ask) if payload.best_ask is not None else None,source='polymarket-wss'))
        elif typ=='last_trade_price':updates.append(self.update_quote(str(payload.token_id),last_price=float(payload.price),source='polymarket-wss'))
        elif typ=='price_change':
            for x in payload.price_changes:updates.append(self.update_quote(str(x.token_id),float(x.best_bid) if x.best_bid is not None else None,float(x.best_ask) if x.best_ask is not None else None,float(x.price),'polymarket-wss'))
        return updates
    def book(self,token_id:str)->OrderBook|None:
        row=self._books.get(token_id)
        if not row:return None
        book,ts=row
        if (datetime.now(timezone.utc)-ts).total_seconds()>self.stale_seconds:return None
        return book
    def quote(self,token_id:str):return self._quotes.get(token_id)
    def snapshot(self):return {'quotes':list(self._quotes.values()),'events':self.events,'last_event_at':self.last_event_at}

class RealtimeEngine:
    """Public market-data engine: official SDK stream first, REST polling fallback."""
    def __init__(self,service,enabled:bool=True,prefer_sdk:bool=True,poll_seconds:float=5.0,stale_seconds:float=20.0,market_limit:int=20):
        self.service=service;self.enabled=bool(enabled);self.prefer_sdk=bool(prefer_sdk);self.poll_seconds=max(.5,float(poll_seconds));self.market_limit=max(1,min(int(market_limit),100));self.cache=RealtimeMarketCache(stale_seconds);self._task=None;self._subscribers=set();self.mode='stopped';self.reconnects=0;self.fallbacks=0;self.last_error=None;self.started_at=None;self.sdk_available=None
    @property
    def running(self):return self._task is not None and not self._task.done()
    def status(self):
        snap=self.cache.snapshot();return {'enabled':self.enabled,'running':self.running,'mode':self.mode,'prefer_sdk':self.prefer_sdk,'sdk_available':self.sdk_available,'poll_seconds':self.poll_seconds,'market_limit':self.market_limit,'reconnects':self.reconnects,'fallbacks':self.fallbacks,'subscribers':len(self._subscribers),'last_error':self.last_error,'started_at':self.started_at,'events':snap['events'],'last_event_at':snap['last_event_at'],'cached_quotes':len(snap['quotes'])}
    def subscribe(self):q=asyncio.Queue(maxsize=8);self._subscribers.add(q);return q
    def unsubscribe(self,q):self._subscribers.discard(q)
    def _broadcast(self,payload):
        for q in tuple(self._subscribers):
            if q.full():
                try:q.get_nowait()
                except asyncio.QueueEmpty:pass
            try:q.put_nowait(payload)
            except asyncio.QueueFull:pass
    async def _discover(self):
        if self.service.s.mode=='demo':markets=DEMO_MARKETS[:self.market_limit]
        else:
            try:markets=await self.service.client.list_markets(self.market_limit)
            except Exception:markets=[]
            if not markets:markets=DEMO_MARKETS[:self.market_limit]
        self.cache.register_markets(markets);return markets
    async def _sdk_loop(self):
        from polymarket import AsyncPublicClient
        from polymarket.streams import MarketSpec
        self.sdk_available=True;markets=await self._discover();tokens=[t for m in markets if m.source=='polymarket' for t in (m.yes_token_id,m.no_token_id) if t]
        if not tokens:raise RuntimeError('no Polymarket token ids available for realtime stream')
        client=AsyncPublicClient();handle=None
        try:
            handle=await client.subscribe(MarketSpec(token_ids=tokens,custom_feature_enabled=True));self.mode='polymarket-wss';self.last_error=None
            async for event in handle:
                for q in self.cache.apply_sdk_event(event):self._broadcast({'type':'quote','data':q})
        finally:
            if handle is not None:
                try:await handle.close()
                except Exception:pass
            await client.close()
    async def _poll_loop(self):
        self.mode='demo-realtime' if self.service.s.mode=='demo' else 'rest-poll'
        while True:
            markets=await self._discover()
            for m in markets:
                if m.yes_token_id:self._broadcast({'type':'quote','data':self.cache.update_quote(m.yes_token_id,last_price=m.yes_price,source=self.mode)})
                if m.no_token_id:self._broadcast({'type':'quote','data':self.cache.update_quote(m.no_token_id,last_price=m.no_price,source=self.mode)})
            self._broadcast({'type':'heartbeat','data':self.status()});await asyncio.sleep(self.poll_seconds)
    async def _run(self):
        self.started_at=datetime.now(timezone.utc).isoformat();backoff=1.0
        while self.enabled:
            try:
                if self.prefer_sdk and self.service.s.mode!='demo':await self._sdk_loop()
                else:await self._poll_loop()
                backoff=1.0
            except asyncio.CancelledError:raise
            except ModuleNotFoundError as exc:
                self.sdk_available=False;self.last_error=f'official realtime SDK unavailable: {exc}';self.fallbacks+=1;await self._poll_loop()
            except Exception as exc:
                self.last_error=str(exc)[:300];self.reconnects+=1;self.fallbacks+=1
                try:await asyncio.wait_for(self._poll_loop(),timeout=max(15.0,self.poll_seconds*3))
                except asyncio.TimeoutError:pass
                except asyncio.CancelledError:raise
                except Exception as poll_exc:self.last_error=f'{self.last_error}; fallback: {poll_exc}'[:300]
                await asyncio.sleep(backoff);backoff=min(30.0,backoff*2)
        self.mode='stopped'
    async def start(self):
        if self.enabled and not self.running:self._task=asyncio.create_task(self._run(),name='polyquant-realtime')
        return self.status()
    async def stop(self):
        if self._task and not self._task.done():
            self._task.cancel()
            try:await self._task
            except asyncio.CancelledError:pass
        self._task=None;self.mode='stopped';return self.status()
