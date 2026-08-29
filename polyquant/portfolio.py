from __future__ import annotations
import uuid
from dataclasses import dataclass
from .models import PaperAccount,PaperPosition,PaperTrade

@dataclass
class _Pos:
    shares:float=0.0
    avg:float=0.0
    mark:float=0.0

class PaperBroker:
    """Paper broker whose state can be rebuilt exactly from persisted trades."""
    def __init__(self,starting_cash:float=10_000.0,fee_bps:float=0.0,slippage_bps:float=5.0):
        self.starting_cash=float(starting_cash);self.fee_bps=float(fee_bps);self.slippage_bps=float(slippage_bps);self.reset()
    def reset(self):
        self.cash=self.starting_cash;self.realized=0.0;self.positions:dict[tuple[str,str],_Pos]={};self.trades:list[PaperTrade]=[]
    def mark(self,market_id:str,outcome:str,price:float):
        if (market_id,outcome) in self.positions:self.positions[(market_id,outcome)].mark=max(.001,min(.999,float(price)))
    def exposure(self)->float:return sum(abs(p.shares*p.mark) for p in self.positions.values())
    def market_exposure(self,market_id:str)->float:return sum(abs(p.shares*p.mark) for (mid,_),p in self.positions.items() if mid==market_id)
    def equity(self)->float:return self.cash+sum(p.shares*p.mark for p in self.positions.values())
    def _apply_trade(self,t:PaperTrade,append:bool=True):
        key=(t.market_id,t.outcome);pos=self.positions.setdefault(key,_Pos(mark=t.price));pos.mark=t.price
        if t.side=='BUY':
            total=t.notional+t.fee
            if total>self.cash+1e-7:raise ValueError('persisted paper trades exceed starting cash')
            old_cost=pos.shares*pos.avg;pos.shares+=t.shares;pos.avg=(old_cost+t.notional)/pos.shares if pos.shares else 0.0;self.cash-=total
        else:
            if t.shares>pos.shares+1e-7:raise ValueError('persisted paper sell exceeds position')
            self.cash+=t.notional-t.fee;self.realized+=(t.price-pos.avg)*t.shares;pos.shares-=t.shares
            if pos.shares<1e-9:pos.shares=0.0;pos.avg=0.0
        if append:self.trades.append(t)
    def restore(self,trades:list[PaperTrade],marks:dict[tuple[str,str],float]|None=None):
        self.reset()
        for t in sorted(trades,key=lambda x:(x.created_at,x.id)):self._apply_trade(t)
        for (mid,outcome),price in (marks or {}).items():self.mark(mid,outcome,price)
        return self.account()
    def execute(self,market_id:str,outcome:str,side:str,notional:float,reference_price:float)->PaperTrade:
        slip=self.slippage_bps/10_000;price=max(.001,min(.999,reference_price*(1+slip if side=='BUY' else 1-slip)));fee=notional*self.fee_bps/10_000;shares=notional/price
        key=(market_id,outcome);pos=self.positions.setdefault(key,_Pos(mark=price))
        if side=='BUY' and notional+fee>self.cash:raise ValueError('insufficient paper cash')
        if side=='SELL' and shares>pos.shares+1e-9:raise ValueError('cannot short in paper')
        t=PaperTrade(id=str(uuid.uuid4()),market_id=market_id,outcome=outcome,side=side,price=price,shares=shares,notional=notional,fee=fee);self._apply_trade(t);return t
    def account(self)->PaperAccount:
        ps=[];unreal=0.0
        for (mid,outcome),p in self.positions.items():
            if p.shares<=0:continue
            u=(p.mark-p.avg)*p.shares;unreal+=u;ps.append(PaperPosition(market_id=mid,outcome=outcome,shares=p.shares,avg_price=p.avg,mark_price=p.mark,market_value=p.shares*p.mark,unrealized_pnl=u))
        return PaperAccount(starting_cash=self.starting_cash,cash=self.cash,equity=self.equity(),exposure=self.exposure(),realized_pnl=self.realized,unrealized_pnl=unreal,positions=ps,trades=self.trades[-100:])
