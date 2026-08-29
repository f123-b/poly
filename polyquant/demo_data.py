from __future__ import annotations
from datetime import datetime, timedelta, timezone
from .models import BookLevel, Market, OrderBook

NOW = datetime.now(timezone.utc)
DEMO_MARKETS = [
    Market(id="demo-fed", question="Will the Fed cut rates at the next meeting?", slug="fed-cut-next-meeting", category="Macro", end_date=NOW+timedelta(days=40), volume=4_800_000, volume_24h=540_000, liquidity=820_000, yes_price=0.43, no_price=0.57, yes_token_id="demo-fed-yes", no_token_id="demo-fed-no", source="demo"),
    Market(id="demo-btc", question="Will Bitcoin trade above $150,000 before year end?", slug="btc-150k-year-end", category="Crypto", end_date=NOW+timedelta(days=110), volume=7_200_000, volume_24h=960_000, liquidity=1_150_000, yes_price=0.38, no_price=0.62, yes_token_id="demo-btc-yes", no_token_id="demo-btc-no", source="demo"),
    Market(id="demo-btc200", question="Will Bitcoin trade above $200,000 before year end?", slug="btc-200k-year-end", category="Crypto", end_date=NOW+timedelta(days=110), volume=2_800_000, volume_24h=310_000, liquidity=520_000, yes_price=0.44, no_price=0.56, yes_token_id="demo-btc200-yes", no_token_id="demo-btc200-no", source="demo"),
    Market(id="demo-ai", question="Will a frontier AI model score above 90% on the benchmark before 2027?", slug="frontier-ai-benchmark", category="Technology", end_date=NOW+timedelta(days=150), volume=1_900_000, volume_24h=210_000, liquidity=360_000, yes_price=0.56, no_price=0.44, yes_token_id="demo-ai-yes", no_token_id="demo-ai-no", source="demo"),
    Market(id="demo-space", question="Will the next heavy-lift launch succeed on its first attempt?", slug="heavy-lift-launch-success", category="Science", end_date=NOW+timedelta(days=55), volume=940_000, volume_24h=78_000, liquidity=145_000, yes_price=0.67, no_price=0.33, yes_token_id="demo-space-yes", no_token_id="demo-space-no", source="demo"),
    Market(id="demo-election", question="Will Candidate A win the national election?", slug="candidate-a-election", category="Politics", end_date=NOW+timedelta(days=75), volume=12_300_000, volume_24h=1_400_000, liquidity=2_200_000, yes_price=0.49, no_price=0.51, yes_token_id="demo-election-yes", no_token_id="demo-election-no", source="demo"),
]

DEMO_IMBALANCE = {"demo-fed": 0.52, "demo-btc": 0.71, "demo-btc200": -0.08, "demo-ai": -0.18, "demo-space": 0.12, "demo-election": -0.31}

def demo_book(market: Market) -> OrderBook:
    center = market.yes_price
    spread = 0.012 if market.liquidity > 500_000 else 0.025
    bid = max(0.01, center - spread/2)
    ask = min(0.99, center + spread/2)
    imbalance = DEMO_IMBALANCE.get(market.id, 0.0)
    base = max(500.0, market.liquidity / 100)
    bid_mult = 1.0 + max(imbalance, 0)
    ask_mult = 1.0 + max(-imbalance, 0)
    return OrderBook(token_id=market.yes_token_id or market.id, bids=[BookLevel(price=round(bid-i*0.01,4), size=base*bid_mult/(i+1)) for i in range(3)], asks=[BookLevel(price=round(ask+i*0.01,4), size=base*ask_mult/(i+1)) for i in range(3)])
