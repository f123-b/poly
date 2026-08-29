from __future__ import annotations
from .backtest import Backtester
from .models import BacktestRequest, ExperimentRequest
from .storage import Storage

class ExperimentRegistry:
    def __init__(self,storage:Storage,backtester:Backtester):self.storage=storage;self.backtester=backtester
    def register(self,req:ExperimentRequest)->dict:
        return self.storage.save_experiment(req.name,req.strategy,req.config,req.metrics,req.notes)
    def list(self,limit:int=50)->list[dict]:return self.storage.experiments(limit)
    def run_demo_grid(self)->dict:
        points=[{"price":.40,"model_probability":.49},{"price":.42,"model_probability":.52},{"price":.46,"model_probability":.54},{"price":.51,"model_probability":.55},{"price":.56,"model_probability":.56},{"price":.59,"model_probability":.56},{"price":.57,"model_probability":.54},{"price":.53,"model_probability":.61},{"price":.49,"model_probability":.60}]
        rows=[]
        for edge in (.03,.05,.08):
            req=BacktestRequest(points=points,position_pct=.10,min_edge=edge,slippage_bps=10)
            result=self.backtester.run(req)
            metrics={"roi":result.roi,"max_drawdown":result.max_drawdown,"trades":result.trades,"win_rate":result.win_rate,"sharpe":result.sharpe}
            row=self.storage.save_experiment(f"demo-edge-{edge:.2f}","probability_edge",{"min_edge":edge,"position_pct":.10,"slippage_bps":10},metrics,"Offline deterministic experiment grid; validates research workflow only.")
            rows.append(row)
        best=max(rows,key=lambda x:(x["metrics"].get("sharpe",0),x["metrics"].get("roi",0)))
        return {"experiments":rows,"best_experiment_id":best["id"],"warning":"Demo experiment results are synthetic workflow validation, not evidence of future profitability."}
