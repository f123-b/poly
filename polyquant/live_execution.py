from __future__ import annotations
import importlib.util
from decimal import Decimal
from datetime import datetime, timezone
import httpx
from .config import Settings

LIVE_ACK = "I_UNDERSTAND_REAL_MONEY_TRADING"
REQUEST_CONFIRMATION = "EXECUTE_LIVE_ORDER"

class PolymarketLiveExecutor:
    """Optional real-money adapter. Fails closed unless every safety gate passes."""
    def __init__(self, settings: Settings):
        self.s = settings

    async def geoblock(self) -> dict:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get("https://polymarket.com/api/geoblock")
            r.raise_for_status()
            data = r.json()
        return {"blocked": bool(data.get("blocked", True)), "country": data.get("country"), "region": data.get("region")}

    async def preflight(self) -> dict:
        reasons=[]; geo=None
        if not self.s.live_execution_enabled:
            reasons.append("Live execution is disabled")
            return {"ready":False,"reasons":reasons,"geoblock":None,"limits":{"max_order_notional":self.s.live_max_order_notional,"max_market_notional":self.s.live_max_market_notional,"max_daily_notional":self.s.live_max_daily_notional}}
        if self.s.live_risk_ack != LIVE_ACK: reasons.append(f"Set POLYQUANT_LIVE_RISK_ACK={LIVE_ACK}")
        if not self.s.live_private_key: reasons.append("Missing POLYQUANT_LIVE_PRIVATE_KEY")
        if not self.s.live_deposit_wallet: reasons.append("Missing POLYQUANT_LIVE_DEPOSIT_WALLET")
        if importlib.util.find_spec("polymarket") is None: reasons.append("Optional SDK missing: install with pip install -e '.[live]'")
        try:
            geo=await self.geoblock()
            if geo["blocked"]: reasons.append(f"Polymarket trading is blocked for {geo.get('country') or 'this location'}")
        except Exception as exc:
            reasons.append(f"Geoblock check failed closed: {str(exc)[:120]}")
        return {"ready":not reasons,"reasons":reasons,"geoblock":geo,"limits":{"max_order_notional":self.s.live_max_order_notional,"max_market_notional":self.s.live_max_market_notional,"max_daily_notional":self.s.live_max_daily_notional}}

    async def place_market_buy(self, token_id: str, notional: float) -> dict:
        gate=await self.preflight()
        if not gate["ready"]: raise RuntimeError("; ".join(gate["reasons"]))
        from polymarket import AsyncSecureClient
        client=await AsyncSecureClient.create(private_key=self.s.live_private_key, wallet=self.s.live_deposit_wallet)
        try:
            result=await client.place_market_order(token_id=token_id, side="BUY", amount=Decimal(str(notional)))
            return {"order_id":getattr(result,"order_id",None),"status":str(getattr(result,"status","accepted")),"token_id":token_id,"side":"BUY","notional":notional,"submitted_at":datetime.now(timezone.utc).isoformat()}
        finally:
            await client.close()
