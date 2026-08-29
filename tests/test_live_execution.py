import asyncio
from pathlib import Path
from polyquant.config import Settings
from polyquant.live_execution import PolymarketLiveExecutor
from polyquant.models import LiveOrderRequest
from polyquant.service import QuantService


def test_live_preflight_disabled_is_fail_closed():
    gate=asyncio.run(PolymarketLiveExecutor(Settings(live_execution_enabled=False)).preflight())
    assert not gate["ready"]
    assert "disabled" in gate["reasons"][0].lower()


def test_live_order_rejected_without_exact_confirmation(tmp_path:Path):
    svc=QuantService(Settings(mode="demo",db_path=str(tmp_path/"live.db"),live_execution_enabled=False))
    req=LiveOrderRequest(market_id="demo-btc",outcome="YES",notional=1,confirmation="NO")
    decision,result=asyncio.run(svc.live_order(req))
    assert not decision.approved
    assert result is None
    assert "confirmation" in decision.reasons[0]
