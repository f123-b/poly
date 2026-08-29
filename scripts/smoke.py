import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from polyquant.config import Settings
from polyquant.service import QuantService

async def main():
    s=Settings(mode="demo",db_path="/tmp/polyquant-smoke.db",scan_limit=3)
    svc=QuantService(s)
    ops=await svc.opportunities(3)
    print(f"OK: {len(ops)} markets; top={ops[0].market.question}; score={ops[0].features.opportunity_score}")

if __name__=="__main__": asyncio.run(main())
