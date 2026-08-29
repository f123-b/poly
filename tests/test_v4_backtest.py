from polyquant.backtest import Backtester
from polyquant.models import BacktestRequest

def test_conservative_backtest_caps_liquidity_and_reports_costs():
    req=BacktestRequest(points=[{'price':.4,'model_probability':.55,'available_liquidity':100},{'price':.5,'model_probability':.50,'available_liquidity':100},{'price':.52,'model_probability':.49,'available_liquidity':100}],starting_cash=10000,position_pct=.5,max_participation=.1,slippage_bps=10,latency_bps=5,fee_bps=5)
    r=Backtester().run(req)
    assert r.trades==1 and r.partial_fills>=1 and r.turnover>0 and r.fees_paid>0 and r.slippage_cost>0

def test_strict_backtest_ignores_liquidity_cap():
    req=BacktestRequest(points=[{'price':.4,'model_probability':.55,'available_liquidity':1},{'price':.5,'model_probability':.49,'available_liquidity':1},{'price':.5,'model_probability':.49,'available_liquidity':1}],execution_mode='strict')
    r=Backtester().run(req); assert r.trades==1
