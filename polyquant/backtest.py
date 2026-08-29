from __future__ import annotations
import math, statistics
from .models import BacktestRequest, BacktestResult

class Backtester:
    def run(self, req: BacktestRequest) -> BacktestResult:
        cash=req.starting_cash; shares=0.0; entry=0.0; trades=0; wins=0; curve=[]
        for i,p in enumerate(req.points):
            price=max(.001,min(.999,p.price)); edge=p.model_probability-price
            equity=cash+shares*price; curve.append(equity)
            if shares==0 and edge>=req.min_edge:
                notional=min(cash, equity*req.position_pct); fill=price*(1+req.slippage_bps/10000); fee=notional*req.fee_bps/10000
                shares=notional/fill; cash-=notional+fee; entry=fill; trades+=1
            elif shares>0 and (edge<=0 or i==len(req.points)-1):
                fill=price*(1-req.slippage_bps/10000); notional=shares*fill; fee=notional*req.fee_bps/10000
                if fill>entry: wins+=1
                cash+=notional-fee; shares=0
            curve[-1]=cash+shares*price
        ending=cash+shares*req.points[-1].price
        peak=curve[0]; mdd=0.0; rets=[]
        for a,b in zip(curve,curve[1:]):
            peak=max(peak,b); mdd=max(mdd,(peak-b)/peak if peak else 0); rets.append((b-a)/a if a else 0)
        sharpe=0.0
        if len(rets)>1 and statistics.pstdev(rets)>0: sharpe=(statistics.mean(rets)/statistics.pstdev(rets))*math.sqrt(len(rets))
        return BacktestResult(starting_cash=req.starting_cash,ending_equity=ending,roi=(ending/req.starting_cash-1),max_drawdown=mdd,trades=trades,win_rate=(wins/trades if trades else 0),sharpe=sharpe,equity_curve=curve)
