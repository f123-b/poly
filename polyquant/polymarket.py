from __future__ import annotations
import json
from datetime import datetime
import httpx
from .models import BookLevel, Market, OrderBook

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"

def _f(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def _json_list(value) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            data = json.loads(value)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []
    return []

def _dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None

class PolymarketDataClient:
    """Read-only public data adapter. Trading credentials never enter this class."""
    def __init__(self, timeout: float = 8.0):
        self.timeout = timeout

    async def list_markets(self, limit: int = 20) -> list[Market]:
        params = {"active":"true","closed":"false","limit":min(limit,100),"order":"volume_24hr","ascending":"false"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(f"{GAMMA}/markets", params=params)
            r.raise_for_status()
            raw = r.json()
        result = []
        for x in raw:
            outcomes = _json_list(x.get("outcomes"))
            prices = _json_list(x.get("outcomePrices"))
            tokens = _json_list(x.get("clobTokenIds"))
            yes_i = next((i for i,v in enumerate(outcomes) if str(v).lower()=="yes"), 0)
            no_i = next((i for i,v in enumerate(outcomes) if str(v).lower()=="no"), 1 if len(outcomes)>1 else 0)
            yes = _f(prices[yes_i] if yes_i < len(prices) else 0.5, 0.5)
            no = _f(prices[no_i] if no_i < len(prices) else 1-yes, 1-yes)
            result.append(Market(
                id=str(x.get("id")), question=x.get("question") or x.get("slug") or "Untitled market",
                slug=x.get("slug") or "", category=x.get("category") or "General", end_date=_dt(x.get("endDate")),
                active=bool(x.get("active", True)), closed=bool(x.get("closed", False)),
                volume=_f(x.get("volumeNum", x.get("volume"))), volume_24h=_f(x.get("volume24hr", x.get("volume24hrClob", 0))),
                liquidity=_f(x.get("liquidityNum", x.get("liquidity"))), yes_price=yes, no_price=no,
                yes_token_id=str(tokens[yes_i]) if yes_i < len(tokens) else None,
                no_token_id=str(tokens[no_i]) if no_i < len(tokens) else None,
                source="polymarket"))
        return result

    async def get_order_book(self, token_id: str) -> OrderBook:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(f"{CLOB}/book", params={"token_id": token_id})
            r.raise_for_status()
            raw = r.json()
        def levels(key):
            out=[]
            for row in raw.get(key, []):
                try: out.append(BookLevel(price=float(row["price"]), size=float(row["size"])))
                except (KeyError, TypeError, ValueError): continue
            return out
        return OrderBook(token_id=token_id, bids=levels("bids"), asks=levels("asks"))

    async def price_history(self, token_id: str, interval: str = "1d", fidelity: int = 60) -> list[tuple[int,float]]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(f"{CLOB}/prices-history", params={"market":token_id,"interval":interval,"fidelity":fidelity})
            r.raise_for_status()
            raw = r.json().get("history", [])
        return [(int(x["t"]), float(x["p"])) for x in raw if "t" in x and "p" in x]
