import asyncio
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from polyquant.backtest import Backtester
from polyquant.config import Settings
from polyquant.experiments import ExperimentRegistry
from polyquant.service import QuantService

async def main():
    db="/tmp/polyquant-smoke.db";Path(db).unlink(missing_ok=True)
    s=Settings(mode="demo",db_path=db,scan_limit=3)
    svc=QuantService(s)
    ops=await svc.opportunities(3)
    assert len(ops)==3
    top=ops[0]
    assert "calibrated_probability" in top.prediction.components
    hist=await svc.market_history(top.market.id)
    assert hist["points"]
    flow=await svc.smart_money_flow(top.market.id)
    assert -1<=flow["score"]<=1
    exp=ExperimentRegistry(svc.storage,Backtester()).run_demo_grid()
    assert len(exp["experiments"])==3
    status=svc.system_status()
    assert status["warehouse"]["market_snapshots"]>=3
    print(f"OK V3: {len(ops)} markets; top={top.market.question}; snapshots={status['warehouse']['market_snapshots']}; experiments={len(exp['experiments'])}")

if __name__=="__main__":asyncio.run(main())
