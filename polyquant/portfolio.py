from __future__ import annotations
import uuid
from dataclasses import dataclass
from .models import PaperAccount,PaperPosition,PaperSettlement,PaperTrade

@dataclass
class _Pos:shares:float=0.0;avg:float=0.0;mark:float=0.0

class PaperBroker:
    def __init__(self,starting_cash:float=10_000.0,fee_bps:float=0.0,slippage_bps:float=5.0):self.starting_cash=float(starting_cash);self.fee_bps=float(fee_bps);self.slippage_bps=float(slippage_bps);self.reset()
    def reset(self):self.cash=self.starting_cash;self.realized=0.0;self.positions={};self.trades=[];self.settlements=[]
    def mark(self,market_id:str,outcome:str,price:float):
        if (market_id,outcome) in self.positions:self.positions[(market_id,outcome)].mark=max(.001,min(.999,float(price)))
    def exposure(self):return sum(abs(p.shares*p.mark) for p in self.positions.values())
    def market_exposure(self,market_id:str):return sum(abs(p.shares*p.mark) for (mid,_),p in self.positions.items() if mid==market_id)
    def equity(self):return self.cash+sum(p.shares*p.mark for p in self.positions.values())
    def _apply_trade(self,t:PaperTrade):
        key=(t.market_id,t.outcome);p=self.positions.setdefault(key,_Pos(mark=t.price));p.mark=t.price
        if t.side=='BUY':
            if t.notional+t.fee>self.cash+1e-7:raise ValueError('persisted paper trades exceed starting cash')
            old=p.shares*p.avg;p.shares+=t.shares;p.avg=(old+t.notional)/p.shares if p.shares else 0;self.cash-=t.notional+t.fee
        else:
            if t.shares>p.shares+1e-7:raise ValueError('persisted paper sell exceeds position')
            self.cash+=t.notional-t.fee;self.realized+=(t.price-p.avg)*t.shares;p.shares-=t.shares
            if p.shares<1e-9:p.shares=0;p.avg=0
        self.trades.append(t)
    def _apply_settlement(self,s:PaperSettlement):
        realized=0.0;payout=0.0
        for (mid,outcome),p in list(self.positions.items()):
            if mid!=s.market_id or p.shares<=0:continue
            final_price=1.0 if outcome==s.outcome else 0.0;value=p.shares*final_price;realized+=(final_price-p.avg)*p.shares;payout+=value;del self.positions[(mid,outcome)]
        self.cash+=payout;self.realized+=realized;self.settlements.append(s)
    def restore(self,trades:list[PaperTrade],marks=None,settlements:list[PaperSettlement]|None=None):
        self.reset();timeline=[(t.created_at,0,t) for t in trades]+[(s.created_at,1,s) for s in (settlements or [])]
        for _,kind,item in sorted(timeline,key=lambda x:(x[0],x[1])):self._apply_trade(item) if kind==0 else self._apply_settlement(item)
        for (mid,outcome),price in (marks or {}).items():self.mark(mid,outcome,price)
        return self.account()
    def execute(self,market_id,outcome,side,notional,reference_price):
        slip=self.slippage_bps/10000;price=max(.001,min(.999,reference_price*(1+slip if side=='BUY' else 1-slip)));fee=notional*self.fee_bps/10000;shares=notional/price;key=(market_id,outcome);p=self.positions.setdefault(key,_Pos(mark=price))
        if side=='BUY' and notional+fee>self.cash:raise ValueError('insufficient paper cash')
        if side=='SELL' and shares>p.shares+1e-9:raise ValueError('cannot short in paper')
        t=PaperTrade(id=str(uuid.uuid4()),market_id=market_id,outcome=outcome,side=side,price=price,shares=shares,notional=notional,fee=fee);self._apply_trade(t);return t
    def settle(self,market_id:str,outcome:str):
        before=self.realized;before_cash=self.cash;s=PaperSettlement(id=str(uuid.uuid4()),market_id=market_id,outcome=outcome);self._apply_settlement(s);s.realized_pnl=self.realized-before;s.cash_payout=self.cash-before_cash;self.settlements[-1]=s;return s
    def account(self):
        ps=[];unreal=0.0
        for (mid,outcome),p in self.positions.items():
            if p.shares<=0:continue
            u=(p.mark-p.avg)*p.shares;unreal+=u;ps.append(PaperPosition(market_id=mid,outcome=outcome,shares=p.shares,avg_price=p.avg,mark_price=p.mark,market_value=p.shares*p.mark,unrealized_pnl=u))
        return PaperAccount(starting_cash=self.starting_cash,cash=self.cash,equity=self.equity(),exposure=self.exposure(),realized_pnl=self.realized,unrealized_pnl=unreal,positions=ps,trades=self.trades[-100:])
