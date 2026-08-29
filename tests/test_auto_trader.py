import asyncio
from pathlib import Path
from polyquant.auto_trader import AutoTrader
from polyquant.config import Settings
from polyquant.service import QuantService


def test_auto_trader_run_once(tmp_path:Path):
    svc=QuantService(Settings(mode='demo',db_path=str(tmp_path/'a.db'),scan_limit=6))
    bot=AutoTrader(svc,interval_seconds=10,order_notional=50,max_trades_per_cycle=2)
    status=asyncio.run(bot.run_once())
    assert status['cycles']==1
    assert status['executed']>=1
    assert svc.broker.account().exposure>0
