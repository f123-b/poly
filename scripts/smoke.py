import asyncio,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from polyquant.backtest import Backtester
from polyquant.config import Settings
from polyquant.maintenance import MaintenanceLoop
from polyquant.models import BacktestRequest,PaperOrderRequest,ValidationGateRequest
from polyquant.service import QuantService
from polyquant.validation import StrategyValidator

async def main():
    with tempfile.TemporaryDirectory() as d:
        db=str(Path(d)/'smoke.db');settings=Settings(mode='demo',smart_money_demo=True,db_path=db,scan_limit=3,maintenance_enabled=False,starting_cash=1000);svc=QuantService(settings);ops=await svc.opportunities(3);assert len(ops)==3
        # persistent starting cash and ledger
        t=svc.broker.execute(ops[0].market.id,'YES','BUY',25,ops[0].market.yes_price);svc.storage.save_trade(t);svc2=QuantService(Settings(mode='demo',db_path=db,starting_cash=9999,scan_limit=3,maintenance_enabled=False));assert svc2.broker.account().starting_cash==1000 and len(svc2.broker.account().trades)==1
        # resolution settles Paper and persists settlement
        rr=svc2.resolve(ops[0].market.id,'YES');assert rr['paper_settlement'] is not None and not svc2.broker.account().positions;svc3=QuantService(settings);assert svc3.storage.stats()['paper_settlements']==1
        cards=svc3.scorecards();assert cards['overall']['samples']>=1
        # resolved market rejects new Paper and creates audit decision
        decision,trade=await svc3.paper_order(PaperOrderRequest(market_id=ops[0].market.id,outcome='YES',notional=10));assert not decision.approved and decision.decision_id and trade is None
        assert svc3.storage.decisions(1)[0]['id']==decision.decision_id
        bt=Backtester().run(BacktestRequest(points=[{'price':.4,'model_probability':.55,'available_liquidity':100},{'price':.5,'model_probability':.49,'available_liquidity':100},{'price':.52,'model_probability':.48,'available_liquidity':100}],fee_bps=5));assert bt.trades==1
        gate=StrategyValidator().evaluate(ValidationGateRequest(resolved_samples=1,paper_trades=1,brier_score=cards['overall']['brier_score'],roi=bt.roi,max_drawdown=bt.max_drawdown,sharpe=bt.sharpe));assert gate['live_unlocked'] is False
        ms=await MaintenanceLoop(svc3,300,True,10).run_once();assert ms['runs']==1
        status=svc3.system_status();assert status['version']=='6.0.0' and status['paper']['settlements']==1 and status['audit']['decisions']>=1
        print(f"OK V6: settled={status['paper']['settlements']} audit={status['audit']['decisions']} cash={status['paper']['cash']:.2f}")
if __name__=='__main__':asyncio.run(main())
