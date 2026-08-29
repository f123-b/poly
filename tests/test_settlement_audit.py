from pathlib import Path
from polyquant.portfolio import PaperBroker
from polyquant.storage import Storage

def test_settlement_pays_winner_and_restores(tmp_path:Path):
    s=Storage(str(tmp_path/'x.db'));b=PaperBroker(1000,slippage_bps=0);t=b.execute('m','YES','BUY',100,.4);s.save_trade(t);sett=b.settle('m','YES');s.save_settlement(sett);a=b.account();assert not a.positions and a.cash==1150 and a.realized_pnl==150
    b2=PaperBroker(1000,slippage_bps=0);b2.restore(s.paper_trades(),{},s.paper_settlements());assert b2.account().cash==a.cash and b2.account().realized_pnl==a.realized_pnl

def test_decision_audit_links_trade(tmp_path:Path):
    s=Storage(str(tmp_path/'a.db'));b=PaperBroker(1000,slippage_bps=0);t=b.execute('m','YES','BUY',10,.5);s.save_trade(t);did=s.save_decision('m',123,'paper','BUY_YES',{'notional':10},{'approved':True},t.id);a=s.trade_audit(t.id);assert a['decision']['id']==did and a['decision']['prediction_id']==123

def test_paper_starting_cash_persists(tmp_path:Path):
    s=Storage(str(tmp_path/'m.db'));assert s.paper_starting_cash(1000)==1000;assert s.paper_starting_cash(5000)==1000
