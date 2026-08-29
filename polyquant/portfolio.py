from __future__ import annotations
import uuid
from dataclasses import dataclass
from .models import PaperAccount, PaperPosition, PaperTrade

@dataclass
class _Pos:
    shares: float=0.0
    avg: float=0.0
    mark: float=0.0

class PaperBroker:
    def __init__(self, starting_cash: float=10_000.0, fee_bps: float=0.0, slippage_bps: float=5.0):
        self.starting_cash=starting_cash; self.cash=starting_cash; self.realized=0.0; self.fee_bps=fee_bps; self.slippage_bps=slippage_bps
        self.positions: dict[tuple[str,str],_Pos]={}; self.trades:list[PaperTrade]=[]
    def mark(self, market_id:str, outcome:str, price:float):
        if (market_id,outcome) in self.positions: self.positions[(market_id,outcome)].mark=price
    def exposure(self)->float: return sum(abs(p.shares*p.mark) for p in self.positions.values())
    def equity(self)->float: return self.cash+sum(p.shares*p.mark for p in self.positions.values())
    def execute(self, market_id:str, outcome:str, side:str, notional:float, reference_price:float)->PaperTrade:
        slip=self.slippage_bps/10_000
        price=max(0.001,min(0.999,reference_price*(1+slip if side=="BUY" else 1-slip)))
        fee=notional*self.fee_bps/10_000; shares=notional/price
        key=(market_id,outcome); pos=self.positions.setdefault(key,_Pos(mark=price)); pos.mark=price
        if side=="BUY":
            if notional+fee>self.cash: raise ValueError("insufficient paper cash")
            old_cost=pos.shares*pos.avg; pos.shares+=shares; pos.avg=(old_cost+notional)/pos.shares; self.cash-=notional+fee
        else:
            if shares>pos.shares+1e-9: raise ValueError("cannot short in paper V1")
            self.cash+=notional-fee; self.realized+=(price-pos.avg)*shares; pos.shares-=shares
            if pos.shares<1e-9: pos.shares=0; pos.avg=0
        t=PaperTrade(id=str(uuid.uuid4()),market_id=market_id,outcome=outcome,side=side,price=price,shares=shares,notional=notional,fee=fee)
        self.trades.append(t); return t
    def account(self)->PaperAccount:
        ps=[]; unreal=0.0
        for (mid,outcome),p in self.positions.items():
            if p.shares<=0: continue
            u=(p.mark-p.avg)*p.shares; unreal+=u
            ps.append(PaperPosition(market_id=mid,outcome=outcome,shares=p.shares,avg_price=p.avg,mark_price=p.mark,market_value=p.shares*p.mark,unrealized_pnl=u))
        return PaperAccount(starting_cash=self.starting_cash,cash=self.cash,equity=self.equity(),exposure=self.exposure(),realized_pnl=self.realized,unrealized_pnl=unreal,positions=ps,trades=self.trades[-100:])
