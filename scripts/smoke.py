import asyncio, sys, tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from polyquant.config import Settings
from polyquant.service import QuantService
from polyquant.models import ExperimentRequest
async def main():
    with tempfile.TemporaryDirectory() as d:
        s=Settings(mode='demo',db_path=str(Path(d)/'polyquant-smoke.db'),scan_limit=3); svc=QuantService(s); ops=await svc.opportunities(3)
        assert len(ops)==3; hist=svc.research_history(limit=20); assert hist['market_snapshots'] and hist['feature_snapshots'] and hist['prediction_snapshots']
        exp=svc.create_experiment(ExperimentRequest(name='smoke',strategy='probability_edge',config={'mode':'demo'},result={'ok':True})); assert exp['id']; status=svc.system_status(); assert status['auto_trade_mode']=='paper-only'
        print(f"OK V3: {len(ops)} markets; snapshots={status['research_store']['prediction_snapshots']}; top={ops[0].market.question}")
if __name__=='__main__': asyncio.run(main())
