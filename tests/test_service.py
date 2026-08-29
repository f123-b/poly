import asyncio
from pathlib import Path
from polyquant.config import Settings
from polyquant.service import QuantService

def test_demo_service(tmp_path:Path):
    s=Settings(mode='demo',db_path=str(tmp_path/'t.db'),scan_limit=5)
    svc=QuantService(s)
    ops=asyncio.run(svc.opportunities(5))
    assert len(ops)==5
    assert all(x.market.source=='demo' for x in ops)
    assert ops[0].features.opportunity_score >= ops[-1].features.opportunity_score or ops[0].prediction.edge >= ops[-1].prediction.edge
