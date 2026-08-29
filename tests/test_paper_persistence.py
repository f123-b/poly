from pathlib import Path
from polyquant.models import PaperTrade
from polyquant.portfolio import PaperBroker
from polyquant.storage import Storage

def test_paper_account_restores_from_trades(tmp_path:Path):
    store=Storage(str(tmp_path/'state.db'));b=PaperBroker(1000,fee_bps=5,slippage_bps=0);t=b.execute('m1','YES','BUY',100,.4);store.save_trade(t)
    restored=PaperBroker(1000,fee_bps=5,slippage_bps=0);restored.restore(store.paper_trades());a=restored.account()
    assert len(a.positions)==1 and len(a.trades)==1
    assert abs(a.cash-b.account().cash)<1e-9
    assert abs(a.positions[0].shares-b.account().positions[0].shares)<1e-9

def test_restore_buy_and_sell_realized_pnl(tmp_path:Path):
    store=Storage(str(tmp_path/'state2.db'));b=PaperBroker(1000,slippage_bps=0);store.save_trade(b.execute('m1','YES','BUY',100,.4));store.save_trade(b.execute('m1','YES','SELL',50,.5));r=PaperBroker(1000,slippage_bps=0);r.restore(store.paper_trades());assert r.account().realized_pnl>0
