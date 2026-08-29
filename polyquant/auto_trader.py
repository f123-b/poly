from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from .models import PaperOrderRequest
from .service import QuantService

class AutoTrader:
    """Automatic PAPER execution loop. It never calls a live exchange executor."""
    def __init__(self, service: QuantService, interval_seconds: int = 60, order_notional: float = 100.0, max_trades_per_cycle: int = 3):
        self.service=service
        self.interval_seconds=max(10,int(interval_seconds))
        self.order_notional=max(1.0,float(order_notional))
        self.max_trades_per_cycle=max(1,int(max_trades_per_cycle))
        self._task: asyncio.Task | None=None
        self.cycles=0; self.executed=0; self.rejected=0; self.last_run:datetime|None=None; self.last_error:str|None=None; self.last_actions:list[dict]=[]

    @property
    def running(self)->bool:
        return self._task is not None and not self._task.done()

    def status(self)->dict:
        return {"running":self.running,"mode":"paper","interval_seconds":self.interval_seconds,"order_notional":self.order_notional,"max_trades_per_cycle":self.max_trades_per_cycle,"cycles":self.cycles,"executed":self.executed,"rejected":self.rejected,"last_run":self.last_run,"last_error":self.last_error,"last_actions":self.last_actions[-10:]}

    async def run_once(self)->dict:
        ops=await self.service.opportunities(max(12,self.service.s.scan_limit))
        actions=[]; placed=0
        for op in ops:
            p=op.prediction
            if p.direction=="PASS": continue
            if placed>=self.max_trades_per_cycle: break
            req=PaperOrderRequest(market_id=op.market.id,outcome=p.direction,side="BUY",notional=self.order_notional)
            decision,trade=await self.service.paper_order(req)
            if decision.approved and trade is not None:
                placed+=1; self.executed+=1
                actions.append({"market_id":op.market.id,"question":op.market.question,"outcome":p.direction,"edge":p.edge,"status":"executed","notional":trade.notional,"price":trade.price})
            else:
                self.rejected+=1
                actions.append({"market_id":op.market.id,"question":op.market.question,"outcome":p.direction,"edge":p.edge,"status":"rejected","reasons":decision.reasons})
        self.cycles+=1; self.last_run=datetime.now(timezone.utc); self.last_error=None; self.last_actions=actions
        return self.status()

    async def _loop(self):
        while True:
            try:
                await self.run_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.last_error=str(exc)[:300]
            await asyncio.sleep(self.interval_seconds)

    async def start(self)->dict:
        if not self.running:
            self._task=asyncio.create_task(self._loop(),name="polyquant-auto-paper")
        return self.status()

    async def stop(self)->dict:
        task=self._task
        if task and not task.done():
            task.cancel()
            try: await task
            except asyncio.CancelledError: pass
        self._task=None
        return self.status()
