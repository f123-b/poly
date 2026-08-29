from __future__ import annotations
import math, statistics
from .models import BacktestRequest, BacktestResult

class Backtester:
    """Conservative single-outcome simulator with explicit liquidity/latency/cost accounting."""
    @staticmethod
    def _capacity(point,requested:float,req:BacktestRequest)->float:
        if req.execution_mode=="strict" or point.available_liquidity is None: return requested
        return min(requested,max(0.0,point.available_liquidity)*req.max_participation)
    def run(self,req:BacktestRequest)->BacktestResult:
        cash=req.starting_cash; shares=0.0; entry=0.0; trades=0; wins=0; curve=[]; fees=0.0; slip_cost=0.0; turnover=0.0; partial=0
        impact_bps=max(0.0,req.slippage_bps)+max(0.0,req.latency_bps)
        for i,p in enumerate(req.points):
            price=max(.001,min(.999,p.price)); edge=p.model_probability-price; equity=cash+shares*price; curve.append(equity)
            if shares==0 and edge>=req.min_edge:
                requested=min(cash,max(0.0,equity*req.position_pct)); notional=self._capacity(p,requested,req)
                if notional+1e-12<requested: partial+=1
                if notional>0:
                    fill=min(.999,price*(1+impact_bps/10000)); fee=notional*req.fee_bps/10000; bought=notional/fill; cash-=notional+fee; shares=bought; entry=fill; trades+=1; fees+=fee; turnover+=notional; slip_cost+=bought*max(0.0,fill-price)
            elif shares>0 and (edge<=0 or i==len(req.points)-1):
                requested=shares*price; cap=self._capacity(p,requested,req); sell_shares=min(shares,cap/max(price,1e-9))
                if sell_shares+1e-12<shares: partial+=1
                if sell_shares>0:
                    fill=max(.001,price*(1-impact_bps/10000)); gross=sell_shares*fill; fee=gross*req.fee_bps/10000; cash+=gross-fee; fees+=fee; turnover+=gross; slip_cost+=sell_shares*max(0.0,price-fill); shares-=sell_shares
                    if shares<=1e-12:
                        if fill>entry: wins+=1
                        shares=0.0
            curve[-1]=cash+shares*price
        ending=cash+shares*max(.001,min(.999,req.points[-1].price)); peak=curve[0] if curve else req.starting_cash; mdd=0.0; rets=[]
        for a,b in zip(curve,curve[1:]): peak=max(peak,b); mdd=max(mdd,(peak-b)/peak if peak else 0); rets.append((b-a)/a if a else 0)
        sharpe=0.0
        if len(rets)>1 and statistics.pstdev(rets)>0: sharpe=(statistics.mean(rets)/statistics.pstdev(rets))*math.sqrt(len(rets))
        return BacktestResult(starting_cash=req.starting_cash,ending_equity=ending,roi=(ending/req.starting_cash-1),max_drawdown=mdd,trades=trades,win_rate=(wins/trades if trades else 0),sharpe=sharpe,equity_curve=curve,fees_paid=fees,slippage_cost=slip_cost,turnover=turnover,partial_fills=partial)
