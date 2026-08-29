from polyquant.backtest import Backtester
from polyquant.models import BacktestRequest

def test_backtest_executes():
    req=BacktestRequest(points=[{"price":.4,"model_probability":.5},{"price":.45,"model_probability":.53},{"price":.52,"model_probability":.54},{"price":.55,"model_probability":.54}])
    r=Backtester().run(req)
    assert r.trades >= 1
    assert len(r.equity_curve) == 4
    assert r.ending_equity > 0
