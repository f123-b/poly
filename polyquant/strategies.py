from __future__ import annotations
import re
from pydantic import BaseModel
from .models import Market, Prediction

class StrategySignal(BaseModel):
    strategy: str
    market_id: str
    action: str
    score: float
    reason: str

class CrossMarketAnomaly(BaseModel):
    lower_market_id: str
    upper_market_id: str
    lower_threshold: float
    upper_threshold: float
    lower_probability: float
    upper_probability: float
    gap: float
    reason: str

class ProbabilityEdgeStrategy:
    def __init__(self,min_edge:float=.05): self.min_edge=min_edge
    def signal(self,p:Prediction)->StrategySignal:
        action=p.direction if p.edge>=self.min_edge else 'PASS'
        return StrategySignal(strategy='probability_edge',market_id=p.market_id,action=action,score=abs(p.edge),reason=f'Model-market edge {p.edge:+.1%}')

class CrossMarketAnalyzer:
    """Detects simple monotonic threshold contradictions (e.g. >150k must be >= >200k)."""
    _num=re.compile(r'\$?([0-9][0-9,]*(?:\.[0-9]+)?)')
    def _signature(self,m:Market):
        q=m.question.lower()
        if not any(k in q for k in ('above','over','greater than','>')): return None
        matches=list(self._num.finditer(q))
        if not matches: return None
        hit=matches[-1]; value=float(hit.group(1).replace(',',''))
        template=q[:hit.start()]+'{threshold}'+q[hit.end():]
        return template,value
    def find(self,markets:list[Market],tolerance:float=.005)->list[CrossMarketAnomaly]:
        groups={}
        for m in markets:
            sig=self._signature(m)
            if sig: groups.setdefault(sig[0],[]).append((sig[1],m))
        out=[]
        for rows in groups.values():
            rows.sort(key=lambda x:x[0])
            for (a,ma),(b,mb) in zip(rows,rows[1:]):
                if mb.yes_price > ma.yes_price + tolerance:
                    out.append(CrossMarketAnomaly(lower_market_id=ma.id,upper_market_id=mb.id,lower_threshold=a,upper_threshold=b,lower_probability=ma.yes_price,upper_probability=mb.yes_price,gap=mb.yes_price-ma.yes_price,reason='更高门槛事件不应比更低门槛事件拥有更高 YES 概率'))
        return out
