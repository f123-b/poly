from __future__ import annotations
import asyncio
from datetime import datetime,timezone
from typing import Any
from .demo_data import DEMO_MARKETS,demo_book
from .models import BookLevel,Market,OrderBook

class RealtimeMarketCache:
    """Read-only realtime quote/order-book cache with strict staleness rules."""
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
        if typ=='book':updates.append(self.update_book(str(payload.token_id),payload.bids,payload.asks,float(payload.last_trade_price) if payload.last_trade_price is not None else None,'polymarket-wss'))
        elif typ=='best_bid_ask':updates.append(self.update_quote(str(payload.token_id),float(payload.best_bid) if payload.best_bid is not None else None,float(payload.best_ask) if payload.best_ask is not None else None,source='polymarket-wss'))
        elif typ=='last_trade_price':updates.append(self.update_quote(str(payload.token_id),last_price=float(payload.price),source='polymarket-wss'))
        elif typ=='price_change':
            for x in payload.price_changes:updates.append(self.update_quote(str(x.token_id),float(x.best_bid) if x.best_bid is not None else None,float(x.best_ask) if x.best_ask is not None else None,float(x.price),'polymarket-wss'))
        return updates
    def _fresh(self,updated_at:str|None)->bool:
        if not updated_at:return False
        try:return (datetime.now(timezone.utc)-datetime.fromisoformat(updated_at.replace('Z','+00:00'))).total_seconds()<=self.stale_seconds
        except (ValueError,TypeError):return False
    def quote(self,token_id:str,fresh_only:bool=True):
        q=self._quotes.get(token_id)
        return q if q and (not fresh_only or self._fresh(q.get('updated_at'))) else None
    @staticmethod
    def _probability(q:dict|None)->float|None:
        if not q:return None
        bid=q.get('best_bid');ask=q.get('best_ask');last=q.get('last_price')
        if bid is not None and ask is not None and 0<=float(bid)<=float(ask)<=1:return (float(bid)+float(ask))/2
        if last is not None and 0<=float(last)<=1:return float(last)
        return None
    def market_prices(self,m:Market)->dict|None:
        y=self._probability(self.quote(m.yes_token_id)) if m.yes_token_id else None;n=self._probability(self.quote(m.no_token_id)) if m.no_token_id else None
        if y is None and n is None:return None
        if y is None:y=1-float(n)
        if n is None:n=1-float(y)
        total=float(y)+float(n)
        if total<=0:return None
        return {'yes_price':max(.001,min(.999,float(y)/total)),'no_price':max(.001,min(.999,float(n)/total)),'source':'realtime-cache'}
    def book(self,token_id:str)->OrderBook|None:
        row=self._books.get(token_id)
        if not row:return None
        book,ts=row
        if (datetime.now(timezone.utc)-ts).total_seconds()>self.stale_seconds:return None
        return book
    def snapshot(self):return {'quotes':list(self._quotes.values()),'events':self.events,'last_event_at':self.last_event_at,'books':len(self._books)}

class RealtimeEngine:
    """Public market-data engine: official SDK WSS first; REST/Demo fallback."""
    def __init__(self,service,enabled=True,prefer_sdk=True,poll_seconds=5.0,stale_seconds=20.0,market_limit=20,book_refresh_limit=5):
        self.service=service;self.enabled=bool(enabled);self.prefer_sdk=bool(prefer_sdk);self.poll_seconds=max(.5,float(poll_seconds));self.market_limit=max(1,min(int(market_limit),100));self.book_refresh_limit=max(0,min(int(book_refresh_limit),20));self.cache=RealtimeMarketCache(stale_seconds);setattr(service,'realtime_cache',self.cache);self._task=None;self._subscribers=set();self.mode='stopped';self.reconnects=0;self.fallbacks=0;self.last_error=None;self.started_at=None;self.sdk_available=None
    @property
    def running(self):return self._task is not None and not self._task.done()
    def status(self):
        s=self.cache.snapshot();return {'enabled':self.enabled,'running':self.running,'mode':self.mode,'prefer_sdk':self.prefer_sdk,'sdk_available':self.sdk_available,'poll_seconds':self.poll_seconds,'market_limit':self.market_limit,'book_refresh_limit':self.book_refresh_limit,'reconnects':self.reconnects,'fallbacks':self.fallbacks,'subscribers':len(self._subscribers),'last_error':self.last_error,'started_at':self.started_at,'events':s['events'],'last_event_at':s['last_event_at'],'cached_quotes':len(s['quotes']),'cached_books':s['books']}
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
    async def _refresh_book(self,m:Market):
        if self.service.s.mode=='demo':
            book=demo_book(m);self.cache.update_book(m.yes_token_id or m.id,book.bids,book.asks,m.yes_price,'demo-realtime');return
        if m.yes_token_id:
            try:
                b=await self.service.client.get_order_book(m.yes_token_id);self.cache.update_book(m.yes_token_id,b.bids,b.asks,m.yes_price,'rest-poll')
            except Exception:pass
    async def _poll_loop(self):
        self.mode='demo-realtime' if self.service.s.mode=='demo' else 'rest-poll'
        while True:
            markets=await self._discover()
            await asyncio.gather(*(self._refresh_book(m) for m in markets[:self.book_refresh_limit]))
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
            except ModuleNotFoundError as exc:self.sdk_available=False;self.last_error=f'official realtime SDK unavailable: {exc}';self.fallbacks+=1;await self._poll_loop()
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
