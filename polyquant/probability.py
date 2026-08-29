from __future__ import annotations
import json
import httpx
from .config import Settings
from .models import FeatureSnapshot, Market, Prediction

def clamp(x, lo=0.02, hi=0.98): return max(lo, min(hi, x))

class ProbabilityEngine:
    """V1 calibrated quant ensemble. Optional LLM acts only as research input, never as executor."""
    def __init__(self, settings: Settings):
        self.settings = settings

    async def predict(self, market: Market, f: FeatureSnapshot) -> Prediction:
        p = market.yes_price
        rationale=[]
        ob_adj = max(-0.04, min(0.04, f.orderbook_imbalance*0.05))
        if abs(ob_adj) >= 0.005:
            rationale.append(f"订单簿失衡修正 {ob_adj:+.1%}")
        quant_adj = ob_adj + (0.5-p)*0.025*f.uncertainty_score
        demo_alpha = {"demo-fed": 0.12, "demo-btc": 0.14, "demo-btc200": -0.06, "demo-ai": -0.10, "demo-space": 0.09, "demo-election": -0.08}.get(market.id, 0.0) if market.source == "demo" else 0.0
        if demo_alpha:
            rationale.append(f"Demo 场景研究偏差 {demo_alpha:+.1%}（仅离线演示）")
        raw = clamp(p + quant_adj + demo_alpha)
        llm = await self._llm_probability(market, p)
        if llm is not None:
            llm_p, note = llm
            raw = clamp(0.75*raw + 0.25*llm_p)
            rationale.append(note)
        confidence = clamp(0.52 + 0.20*f.liquidity_score + 0.12*f.volume_score + 0.10*min(1,abs(f.orderbook_imbalance)), 0.50, 0.90)
        calibrated = clamp(p + (raw-p)*0.72)
        yes_edge = calibrated-p
        no_edge = (1-calibrated)-market.no_price
        if max(yes_edge,no_edge) < self.settings.min_edge:
            direction="PASS"; edge=max(yes_edge,no_edge)
        elif yes_edge >= no_edge:
            direction="YES"; edge=yes_edge
        else:
            direction="NO"; edge=no_edge
        rationale.append("V1 概率经 28% 向市场价格收缩，降低过度自信")
        return Prediction(market_id=market.id, market_probability=p, raw_probability=raw, model_probability=calibrated, confidence=confidence, edge=edge, direction=direction, rationale=rationale)

    async def _llm_probability(self, market: Market, market_p: float):
        s=self.settings
        if not (s.llm_base_url and s.llm_api_key and s.llm_model): return None
        url=s.llm_base_url.rstrip("/")+"/chat/completions"
        prompt=("You are a conservative prediction-market research model. Estimate the probability of YES. "
                "Return ONLY JSON: {\"probability\":0.0,\"note\":\"short evidence-based note\"}. "
                f"Question: {market.question}\nMarket implied probability: {market_p:.4f}. "
                "Do not give trading instructions; express uncertainty and avoid inventing facts.")
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r=await c.post(url,headers={"Authorization":f"Bearer {s.llm_api_key}"},json={"model":s.llm_model,"messages":[{"role":"user","content":prompt}],"temperature":0.2})
                r.raise_for_status(); text=r.json()["choices"][0]["message"]["content"]
            data=json.loads(text.strip().strip("`")); prob=float(data["probability"])
            if 0<=prob<=1: return prob, "AI Research: "+str(data.get("note","已纳入低权重研究概率"))[:180]
        except Exception:
            return None
        return None
