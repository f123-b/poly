from __future__ import annotations

import re
from dataclasses import dataclass
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
    """Deterministic relation extractor for common prediction-market constraints."""

    MONEY = re.compile(r"\$?([0-9]+(?:\.[0-9]+)?)\s*([kmb])?", re.I)

    @classmethod
    def _threshold(cls, text: str) -> float | None:
        matches = list(cls.MONEY.finditer(text.replace(",", "")))
        if not matches:
            return None
        value = float(matches[-1].group(1))
        suffix = (matches[-1].group(2) or "").lower()
        return value * {"": 1.0, "k": 1e3, "m": 1e6, "b": 1e9}[suffix]

    @staticmethod
    def _normalized(text: str) -> set[str]:
        stop = {"will", "above", "over", "below", "under", "before", "after", "by", "the", "a", "an", "be", "hit", "reach"}
        return {x for x in re.findall(r"[a-z]+", text.lower()) if len(x) > 2 and x not in stop}

    def relations(self, markets: list[Market]) -> list[MarketRelation]:
        out: list[MarketRelation] = []
        for idx, left in enumerate(markets):
            for right in markets[idx + 1 :]:
                lt, rt = self._normalized(left.question), self._normalized(right.question)
                overlap = len(lt & rt) / max(1, min(len(lt), len(rt)))
                if overlap < 0.5:
                    continue
                lth, rth = self._threshold(left.question), self._threshold(right.question)
                lower_left = left.question.lower()
                lower_right = right.question.lower()
                if lth is not None and rth is not None and lth != rth and ("above" in lower_left or "over" in lower_left or "reach" in lower_left or "hit" in lower_left) and ("above" in lower_right or "over" in lower_right or "reach" in lower_right or "hit" in lower_right):
                    if lth < rth:
                        out.append(MarketRelation(left_market_id=right.id, right_market_id=left.id, relation="subset", confidence=min(0.95, 0.65 + overlap * 0.3), explanation=f"{right.question!r} implies the lower threshold market {left.question!r}."))
                    else:
                        out.append(MarketRelation(left_market_id=left.id, right_market_id=right.id, relation="subset", confidence=min(0.95, 0.65 + overlap * 0.3), explanation=f"{left.question!r} implies the lower threshold market {right.question!r}."))
                elif overlap >= 0.75:
                    out.append(MarketRelation(left_market_id=left.id, right_market_id=right.id, relation="same_event", confidence=min(0.9, overlap), explanation="Questions share most material tokens and likely refer to the same underlying event."))
        return out

    def anomalies(self, markets: list[Market]) -> list[GraphAnomaly]:
        by_id = {m.id: m for m in markets}
        out: list[GraphAnomaly] = []
        for relation in self.relations(markets):
            left = by_id[relation.left_market_id]
            right = by_id[relation.right_market_id]
            if relation.relation == "subset" and left.yes_price > right.yes_price + 0.01:
                gap = left.yes_price - right.yes_price
                out.append(GraphAnomaly(
                    left_market_id=left.id,
                    right_market_id=right.id,
                    relation="subset",
                    severity=min(1.0, gap / 0.15),
                    explanation=f"Subset probability {left.yes_price:.1%} exceeds superset probability {right.yes_price:.1%} by {gap:.1%}.",
                ))
        return sorted(out, key=lambda x: x.severity, reverse=True)
