from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .backtest import Backtester
from .calibration import calibration_metrics
from .smart_money import SmartMoneyClient
from .strategies import CrossMarketAnalyzer
from .config import get_settings
from .models import BacktestRequest, PaperOrderRequest
from .service import QuantService

ROOT=Path(__file__).resolve().parent.parent
settings=get_settings(); service=QuantService(settings); backtester=Backtester(); cross_market=CrossMarketAnalyzer(); smart_money=SmartMoneyClient()
app=FastAPI(title="PolyQuant Intelligence",version="1.0.0")

@app.get("/api/health")
async def health(): return {"ok":True,"mode":settings.mode,"data_source":service.last_source,"live_execution":False,"version":"1.0.0"}

@app.get("/api/markets")
async def markets(): return await service.markets()

@app.get("/api/opportunities")
async def opportunities(limit:int=12): return await service.opportunities(min(max(limit,1),30))

@app.get("/api/markets/{market_id}")
async def market_detail(market_id:str):
    try: return await service.get_market(market_id)
    except KeyError: raise HTTPException(404,"market not found")

@app.get("/api/cross-market/anomalies")
async def cross_market_anomalies():
    ms=await service.markets()
    return cross_market.find(ms)

@app.get("/api/smart-money/leaderboard")
async def smart_money_leaderboard(category:str="OVERALL",time_period:str="MONTH",limit:int=10):
    try:
        return await smart_money.leaderboard(category,time_period,limit)
    except Exception as exc:
        raise HTTPException(502,f"smart-money data unavailable: {exc}")

@app.get("/api/calibration/demo")
async def calibration_demo():
    return calibration_metrics([.18,.28,.36,.48,.57,.64,.72,.81],[0,0,1,0,1,1,1,1],bins=5)

@app.get("/api/paper/account")
async def paper_account(): return service.broker.account()

@app.post("/api/paper/orders")
async def paper_order(req:PaperOrderRequest):
    decision,trade=await service.paper_order(req)
    if not decision.approved: raise HTTPException(422,detail=decision.model_dump())
    return {"risk":decision,"trade":trade,"account":service.broker.account()}

@app.post("/api/backtest")
async def backtest(req:BacktestRequest): return backtester.run(req)

@app.post("/api/backtest/demo")
async def demo_backtest():
    req=BacktestRequest(points=[
        {"price":.40,"model_probability":.49},{"price":.42,"model_probability":.52},{"price":.46,"model_probability":.54},
        {"price":.51,"model_probability":.55},{"price":.56,"model_probability":.56},{"price":.59,"model_probability":.56},
        {"price":.57,"model_probability":.54}], position_pct=.12, min_edge=.05)
    return backtester.run(req)

web=ROOT/"web"
if web.exists():
    app.mount("/assets",StaticFiles(directory=web),name="assets")
    @app.get("/")
    async def root(): return FileResponse(web/"index.html")
