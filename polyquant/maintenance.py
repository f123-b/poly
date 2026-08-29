from __future__ import annotations
import asyncio
from datetime import datetime,timezone

class MaintenanceLoop:
    """Low-frequency maintenance: retention + conservative resolution sync."""
    def __init__(self,service,interval_seconds:int=3600,resolution_sync:bool=True,resolution_limit:int=100):
        self.service=service;self.interval_seconds=max(300,int(interval_seconds));self.resolution_sync=bool(resolution_sync);self.resolution_limit=max(1,min(int(resolution_limit),100));self._task=None;self.runs=0;self.last_run=None;self.last_error=None;self.last_result=None
    @property
    def running(self):return self._task is not None and not self._task.done()
    def status(self):return {'running':self.running,'interval_seconds':self.interval_seconds,'resolution_sync':self.resolution_sync,'runs':self.runs,'last_run':self.last_run,'last_error':self.last_error,'last_result':self.last_result}
    async def run_once(self):
        pruned=self.service.storage.prune_research(self.service.s.snapshot_retention_per_market)
        resolution={'source':'disabled','scanned':0,'saved':0}
        if self.resolution_sync:
            try:resolution=await self.service.sync_resolutions(self.resolution_limit)
            except Exception as exc:resolution={'source':'error','scanned':0,'saved':0,'error':str(exc)[:300]}
        self.runs+=1;self.last_run=datetime.now(timezone.utc);self.last_result={'pruned':pruned,'resolution':resolution,'calibration':self.service.historical_calibration()};self.last_error=resolution.get('error');return self.status()
    async def _loop(self):
        while True:
            try:await self.run_once()
            except asyncio.CancelledError:raise
            except Exception as exc:self.last_error=str(exc)[:300]
            await asyncio.sleep(self.interval_seconds)
    async def start(self):
        if not self.running:self._task=asyncio.create_task(self._loop(),name='polyquant-maintenance')
        return self.status()
    async def stop(self):
        if self._task and not self._task.done():
            self._task.cancel()
            try:await self._task
            except asyncio.CancelledError:pass
        self._task=None;return self.status()
