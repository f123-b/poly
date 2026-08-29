from __future__ import annotations
import re
from typing import Literal
from pydantic import BaseModel
from .models import Market

RelationType = Literal["subset", "mutually_exclusive", "same_event"]

class MarketRelation(BaseModel):
    left_market_id: str
    right_market_id: str
    relation: RelationType
    confidence: float
    explanation: str

class GraphAnomaly(BaseModel):
    left_market_id: str
    right_market_id: str
    relation: RelationType
    severity: float
    explanation: str

class MarketGraph:
    MONEY = re.compile(r"\$\s*([0-9][0-9,]*(?:\.[0-9]+)?)|([0-9]+(?:\.[0-9]+)?)\s*([kmb])\b", re.I)
    @classmethod
    def _threshold(cls,text:str)->float|None:
        matches=list(cls.MONEY.finditer(text))
        if not matches: return None
        hit=matches[-1]
        if hit.group(1): return float(hit.group(1).replace(",",""))
        value=float(hit.group(2)); suffix=(hit.group(3) or "").lower(); return value*{"k":1e3,"m":1e6,"b":1e9}[suffix]
    @staticmethod
    def _normalized(text:str)->set[str]:
        stop={"will","above","over","below","under","before","after","by","the","a","an","be","hit","reach","year","end"}
        return {x for x in re.findall(r"[a-z]+",text.lower()) if len(x)>2 and x not in stop}
    def relations(self,markets:list[Market])->list[MarketRelation]:
        out=[]
        for idx,left in enumerate(markets):
            for right in markets[idx+1:]:
                lt,rt=self._normalized(left.question),self._normalized(right.question); overlap=len(lt&rt)/max(1,min(len(lt),len(rt)))
                if overlap<.5: continue
                lth,rth=self._threshold(left.question),self._threshold(right.question); lq,rq=left.question.lower(),right.question.lower(); upward=("above","over","reach","hit","greater than")
                if lth is not None and rth is not None and lth!=rth and any(k in lq for k in upward) and any(k in rq for k in upward):
                    high,low=(left,right) if lth>rth else (right,left)
                    out.append(MarketRelation(left_market_id=high.id,right_market_id=low.id,relation="subset",confidence=min(.95,.65+overlap*.3),explanation=f"{high.question!r} implies the lower-threshold market {low.question!r}."))
                elif overlap>=.75:
                    out.append(MarketRelation(left_market_id=left.id,right_market_id=right.id,relation="same_event",confidence=min(.9,overlap),explanation="Questions share most material tokens and likely refer to the same underlying event."))
        return out
    def anomalies(self,markets:list[Market])->list[GraphAnomaly]:
        by_id={m.id:m for m in markets}; out=[]
        for relation in self.relations(markets):
            left,right=by_id[relation.left_market_id],by_id[relation.right_market_id]
            if relation.relation=="subset" and left.yes_price>right.yes_price+.01:
                gap=left.yes_price-right.yes_price; out.append(GraphAnomaly(left_market_id=left.id,right_market_id=right.id,relation="subset",severity=min(1.,gap/.15),explanation=f"Subset probability {left.yes_price:.1%} exceeds superset probability {right.yes_price:.1%} by {gap:.1%}."))
        return sorted(out,key=lambda x:x.severity,reverse=True)
