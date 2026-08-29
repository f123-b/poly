from __future__ import annotations
from .models import ValidationGateRequest

class StrategyValidator:
    def evaluate(self,r:ValidationGateRequest)->dict:
        checks=[]
        def add(name,ok,value,threshold): checks.append({'name':name,'passed':bool(ok),'value':value,'threshold':threshold})
        add('resolved_samples',r.resolved_samples>=r.min_resolved_samples,r.resolved_samples,f'>={r.min_resolved_samples}')
        add('paper_trades',r.paper_trades>=r.min_paper_trades,r.paper_trades,f'>={r.min_paper_trades}')
        add('brier_score',r.brier_score is not None and r.brier_score<=r.max_brier_score,r.brier_score,f'<={r.max_brier_score}')
        add('roi',r.roi is not None and r.roi>=r.min_roi,r.roi,f'>={r.min_roi}')
        add('max_drawdown',r.max_drawdown is not None and r.max_drawdown<=r.max_allowed_drawdown,r.max_drawdown,f'<={r.max_allowed_drawdown}')
        add('sharpe',r.sharpe is not None and r.sharpe>=r.min_sharpe,r.sharpe,f'>={r.min_sharpe}')
        passed=all(x['passed'] for x in checks)
        stage='shadow-live' if passed else ('paper' if r.paper_trades>=max(20,r.min_paper_trades//4) else 'research')
        return {'passed':passed,'recommended_stage':stage,'checks':checks,'live_unlocked':False,'note':'Passing this research gate never enables real-money execution automatically.'}
