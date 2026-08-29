from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from pydantic import BaseModel, Field

from .models import Market

class EvidenceItem(BaseModel):
    id: str
    title: str
    summary: str = ""
    source: str = "demo"
    url: str | None = None
    published_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    entities: list[str] = Field(default_factory=list)
    reliability: float = Field(default=0.5, ge=0.0, le=1.0)
    sentiment: float = Field(default=0.0, ge=-1.0, le=1.0)

class MarketEvidence(BaseModel):
    market_id: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    evidence_score: float = 0.0
    freshness_score: float = 0.0
    net_sentiment: float = 0.0

@dataclass(frozen=True)
class KeywordRule:
    token: str
    weight: float

class EventIntelligence:
    """Provider-neutral, deterministic evidence ingestion and market matching."""
    STOP = {"will","the","a","an","of","to","in","on","by","for","before","after","during","is","are","be","and","or","with","at","from","this","that","yes","no","market","happen","occur","2026","2027"}
    def __init__(self,feed_url:str|None=None,timeout:float=8.0): self.feed_url=feed_url; self.timeout=timeout
    @staticmethod
    def _id(title:str,source:str,published_at:str)->str:
        return hashlib.sha256(f"{source}|{published_at}|{title}".encode()).hexdigest()[:20]
    @classmethod
    def _tokens(cls,text:str)->set[str]:
        return {t for t in re.findall(r"[a-z0-9$%]+",text.lower()) if len(t)>=3 and t not in cls.STOP}
    @classmethod
    def relevance(cls,market:Market,item:EvidenceItem)->float:
        q=cls._tokens(f"{market.question} {market.category}"); e=cls._tokens(f"{item.title} {item.summary} {' '.join(item.entities)}")
        if not q or not e: return 0.0
        overlap=len(q&e)/max(1,len(q)); title_bonus=min(.25,.05*len(cls._tokens(item.title)&q)); return min(1.0,overlap+title_bonus)
    @staticmethod
    def _parse_time(value:object)->datetime:
        if isinstance(value,datetime): return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value,str) and value:
            try:
                p=datetime.fromisoformat(value.replace("Z","+00:00")); return p if p.tzinfo else p.replace(tzinfo=timezone.utc)
            except ValueError: pass
        return datetime.now(timezone.utc)
    @classmethod
    def _coerce(cls,row:dict)->EvidenceItem:
        published=cls._parse_time(row.get("published_at") or row.get("publishedAt")); title=str(row.get("title") or row.get("headline") or "Untitled event"); source=str(row.get("source") or "external")
        return EvidenceItem(id=str(row.get("id") or cls._id(title,source,published.isoformat())),title=title,summary=str(row.get("summary") or row.get("description") or ""),source=source,url=row.get("url"),published_at=published,entities=[str(x) for x in row.get("entities",[]) if x],reliability=max(0.0,min(1.0,float(row.get("reliability",.6)))),sentiment=max(-1.0,min(1.0,float(row.get("sentiment",0.0)))))
    async def fetch(self)->list[EvidenceItem]:
        if not self.feed_url: return self.demo_feed()
        async with httpx.AsyncClient(timeout=self.timeout,follow_redirects=True) as client:
            r=await client.get(self.feed_url); r.raise_for_status(); payload=r.json()
        rows=payload.get("items",[]) if isinstance(payload,dict) else payload
        if not isinstance(rows,list): raise ValueError("event feed must be a list or {'items': [...]} JSON")
        return [self._coerce(x) for x in rows if isinstance(x,dict)]
    async def for_market(self,market:Market,limit:int=8,items:list[EvidenceItem]|None=None)->MarketEvidence:
        items=items if items is not None else await self.fetch(); scored=[(self.relevance(market,item),item) for item in items]; selected=[(r,i) for r,i in scored if r>0]
        selected.sort(key=lambda x:(x[0]*x[1].reliability,x[1].published_at),reverse=True); selected=selected[:max(1,limit)]
        if not selected: return MarketEvidence(market_id=market.id)
        now=datetime.now(timezone.utc); weighted=[]; freshness=[]
        for relevance,item in selected:
            age=max(0.0,(now-item.published_at).total_seconds()/3600); fresh=1/(1+age/24); weight=relevance*item.reliability*fresh; weighted.append((weight,item.sentiment)); freshness.append(fresh)
        total=sum(w for w,_ in weighted) or 1.0; net=sum(w*s for w,s in weighted)/total
        return MarketEvidence(market_id=market.id,evidence=[i for _,i in selected],evidence_score=min(1.0,sum(w for w,_ in weighted)),freshness_score=sum(freshness)/len(freshness),net_sentiment=net)
    @staticmethod
    def demo_feed()->list[EvidenceItem]:
        now=datetime.now(timezone.utc); rows=[
            {"title":"Bitcoin volatility remains elevated around major price thresholds","summary":"Crypto markets are watching Bitcoin threshold contracts and liquidity conditions.","source":"demo-crypto","published_at":now.isoformat(),"entities":["Bitcoin","BTC"],"reliability":.72,"sentiment":.25},
            {"title":"Federal Reserve policy expectations shift with incoming inflation data","summary":"Rate-path expectations moved after macroeconomic releases.","source":"demo-macro","published_at":now.isoformat(),"entities":["Federal Reserve","Fed","rates"],"reliability":.8,"sentiment":.05},
            {"title":"Election polling update changes candidate implied odds","summary":"New polling data changed aggregate election forecasts.","source":"demo-politics","published_at":now.isoformat(),"entities":["election","polling"],"reliability":.68,"sentiment":0.0},]
        return [EventIntelligence._coerce(x) for x in rows]
