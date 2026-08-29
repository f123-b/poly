from __future__ import annotations
from .config import Settings
from .models import FeatureSnapshot, Prediction, RiskDecision

def fractional_kelly(prob: float, price: float, fraction: float) -> float:
    if not (0 < price < 1): return 0.0
    b=(1-price)/price
    q=1-prob
    k=(b*prob-q)/b
    return max(0.0,k)*fraction

class RiskEngine:
    def __init__(self, settings: Settings): self.s=settings
    def evaluate(self, prediction: Prediction, features: FeatureSnapshot, equity: float, current_exposure: float, requested_notional: float) -> RiskDecision:
        reasons=[]
        if prediction.direction == "PASS": reasons.append("预测 Edge 未达到开仓阈值")
        if prediction.edge < self.s.min_edge: reasons.append(f"Edge {prediction.edge:.1%} < {self.s.min_edge:.1%}")
        if prediction.confidence < self.s.min_confidence: reasons.append(f"Confidence {prediction.confidence:.1%} < {self.s.min_confidence:.1%}")
        if features.spread > self.s.max_spread: reasons.append(f"Spread {features.spread:.1%} > {self.s.max_spread:.1%}")
        max_single=equity*self.s.max_single_market_pct
        remaining=max(0.0,equity*self.s.max_total_exposure_pct-current_exposure)
        max_notional=min(max_single,remaining)
        if requested_notional > max_notional+1e-9: reasons.append(f"请求仓位超过硬上限 ${max_notional:.2f}")
        k=fractional_kelly(prediction.model_probability if prediction.direction=="YES" else 1-prediction.model_probability, prediction.market_probability if prediction.direction=="YES" else 1-prediction.market_probability, self.s.fractional_kelly)
        suggested=min(max_notional,equity*k*prediction.confidence)
        return RiskDecision(approved=not reasons,reasons=reasons,max_notional=max_notional,suggested_notional=suggested)
