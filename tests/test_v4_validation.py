from polyquant.models import ValidationGateRequest
from polyquant.validation import StrategyValidator

def test_validation_gate_never_unlocks_live():
    r=StrategyValidator().evaluate(ValidationGateRequest(resolved_samples=200,paper_trades=200,brier_score=.2,roi=.1,max_drawdown=.05,sharpe=1.2))
    assert r['passed'] is True and r['recommended_stage']=='shadow-live' and r['live_unlocked'] is False

def test_validation_gate_rejects_weak_sample():
    r=StrategyValidator().evaluate(ValidationGateRequest(resolved_samples=5,paper_trades=4,brier_score=.3,roi=-.1,max_drawdown=.3,sharpe=-.2)); assert not r['passed'] and r['recommended_stage']=='research'
