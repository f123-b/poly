import asyncio,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from polyquant.analytics import ModelAnalytics
from polyquant.backtest import Backtester
from polyquant.config import Settings
from polyquant.maintenance import MaintenanceLoop
from polyquant.models import BacktestRequest,ValidationGateRequest
from polyquant.service import QuantService
from polyquant.validation import StrategyValidator

async def main():
    with tempfile.TemporaryDirectory() as d:
        db=str(Path(d)/'smoke.db');settings=Settings(mode='demo',smart_money_demo=True,db_path=db,scan_limit=3,maintenance_enabled=False);svc=QuantService(settings);ops=await svc.opportunities(3);assert len(ops)==3
        hist=svc.research_history(ops[0].market.id,20);assert hist['market'] and hist['predictions'] and hist['features']
        trade=svc.broker.execute(ops[0].market.id,'YES','BUY',25,ops[0].market.yes_price);svc.storage.save_trade(trade);svc2=QuantService(settings);assert len(svc2.broker.account().trades)==1 and svc2.broker.account().cash<settings.starting_cash
        svc2.resolve(ops[0].market.id,'YES');cards=svc2.scorecards();assert cards['overall']['samples']>=1;assert svc2.prediction_dataset()
        bt=Backtester().run(BacktestRequest(points=[{'price':.4,'model_probability':.55,'available_liquidity':100},{'price':.5,'model_probability':.49,'available_liquidity':100},{'price':.52,'model_probability':.48,'available_liquidity':100}],fee_bps=5));assert bt.trades==1 and bt.turnover>0
        gate=StrategyValidator().evaluate(ValidationGateRequest(resolved_samples=1,paper_trades=1,brier_score=cards['overall']['brier_score'],roi=bt.roi,max_drawdown=bt.max_drawdown,sharpe=bt.sharpe));assert gate['live_unlocked'] is False
        maint=MaintenanceLoop(svc2,300,True,10);ms=await maint.run_once();assert ms['runs']==1 and ms['last_result']['resolution']['source']=='demo'
        status=svc2.system_status();assert status['version']=='5.0.0' and status['paper']['persistent'] is True
        print(f"OK V5: markets={len(ops)} restored_trades={len(svc2.broker.account().trades)} scorecard={cards['overall']['samples']} maintenance={ms['runs']}")
if __name__=='__main__':asyncio.run(main())
