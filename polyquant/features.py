from __future__ import annotations
import math
from .models import FeatureSnapshot, Market, OrderBook

def _clamp(x: float, lo=0.0, hi=1.0) -> float:
    return max(lo, min(hi, x))

class FeatureEngine:
    def compute(self, market: Market, book: OrderBook | None = None) -> FeatureSnapshot:
        best_bid = max((x.price for x in book.bids), default=None) if book else None
        best_ask = min((x.price for x in book.asks), default=None) if book else None
        spread = (best_ask-best_bid) if best_bid is not None and best_ask is not None else 0.03
        bid_depth = sum(x.size for x in (book.bids[:5] if book else []))
        ask_depth = sum(x.size for x in (book.asks[:5] if book else []))
        denom = bid_depth + ask_depth
        imbalance = (bid_depth-ask_depth)/denom if denom else 0.0
        liquidity_score = _clamp(math.log10(max(market.liquidity,1))/6)
        volume_score = _clamp(math.log10(max(market.volume_24h,1))/6)
        uncertainty = 1.0 - min(1.0, abs(market.yes_price-0.5)*2)
        spread_score = 1.0 - _clamp(spread/0.10)
        opportunity = 100*(0.28*liquidity_score + 0.22*volume_score + 0.18*uncertainty + 0.17*abs(imbalance) + 0.15*spread_score)
        return FeatureSnapshot(market_id=market.id, market_probability=market.yes_price, best_bid=best_bid, best_ask=best_ask, spread=spread, bid_depth=bid_depth, ask_depth=ask_depth, orderbook_imbalance=imbalance, liquidity_score=liquidity_score, volume_score=volume_score, uncertainty_score=uncertainty, opportunity_score=round(opportunity,2))
