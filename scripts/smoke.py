import asyncio,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from polyquant.backtest import Backtester
from polyquant.config import Settings
from polyquant.models import BacktestRequest,ValidationGateRequest
from polyquant.service import QuantService
from polyquant.validation import StrategyValidator
async def main():
    with tempfile.TemporaryDirectory() as d:
        svc=QuantService(Settings(mode='demo',smart_money_demo=True,db_path=str(Path(d)/'smoke.db'),scan_limit=3));ops=await svc.opportunities(3);assert len(ops)==3
        hist=svc.research_history(ops[0].market.id,20);assert hist['market'] and hist['predictions'] and hist['features']
        bt=Backtester().run(BacktestRequest(points=[{'price':.4,'model_probability':.55,'available_liquidity':100},{'price':.5,'model_probability':.49,'available_liquidity':100},{'price':.52,'model_probability':.48,'available_liquidity':100}],fee_bps=5));assert bt.trades==1 and bt.turnover>0
        gate=StrategyValidator().evaluate(ValidationGateRequest(resolved_samples=0,paper_trades=0));assert gate['recommended_stage']=='research' and gate['live_unlocked'] is False
        sync=await svc.sync_resolutions();assert sync['source']=='demo';status=svc.system_status();assert status['version']=='4.0.0' and status['auto_execution']=='paper-only'
        print(f"OK V4: markets={len(ops)} snapshots={status['warehouse']['predictions']} partial_fills={bt.partial_fills} gate={gate['recommended_stage']}")
if __name__=='__main__':asyncio.run(main())
