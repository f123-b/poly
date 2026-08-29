from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI,HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .backtest import Backtester
from .auto_trader import AutoTrader
from .calibration import calibration_metrics
from .strategies import CrossMarketAnalyzer
from .config import get_settings
from .experiments import ExperimentRegistry
from .validation import StrategyValidator
from .models import BacktestRequest,ExperimentRequest,LiveOrderRequest,PaperOrderRequest,ResolveMarketRequest,ValidationGateRequest
from .service import QuantService
ROOT=Path(__file__).resolve().parent.parent
settings=get_settings();service=QuantService(settings);backtester=Backtester();cross_market=CrossMarketAnalyzer();experiments=ExperimentRegistry(service.storage,backtester);validator=StrategyValidator();auto_trader=AutoTrader(service,settings.auto_interval_seconds,settings.auto_order_notional,settings.auto_max_trades_per_cycle)
app=FastAPI(title='PolyQuant Intelligence',version='4.0.0')
@app.get('/api/health')
async def health():return {'ok':True,'mode':settings.mode,'data_source':service.last_source,'live_execution':settings.live_execution_enabled,'event_feed':'external' if settings.event_feed_url else 'demo','version':'4.0.0'}
@app.get('/api/system/status')
async def system_status():return service.system_status()
@app.get('/api/markets')
async def markets():return await service.markets()
@app.get('/api/opportunities')
async def opportunities(limit:int=12):return await service.opportunities(min(max(limit,1),30))
@app.get('/api/markets/{market_id}')
async def market_detail(market_id:str):
    try:return await service.get_market(market_id)
    except KeyError:raise HTTPException(404,'market not found')
@app.get('/api/markets/{market_id}/history')
async def market_history(market_id:str,limit:int=240):
    try:return await service.market_history(market_id,min(max(limit,1),5000))
    except KeyError:raise HTTPException(404,'market not found')
@app.get('/api/markets/{market_id}/research-history')
async def research_history(market_id:str,limit:int=100):return service.research_history(market_id,min(max(limit,1),500))
@app.get('/api/markets/{market_id}/evidence')
async def market_evidence(market_id:str):
    try:return await service.market_evidence(market_id)
    except KeyError:raise HTTPException(404,'market not found')
@app.get('/api/markets/{market_id}/smart-money')
async def market_smart_money(market_id:str):
    try:return await service.smart_money_flow(market_id)
    except KeyError:raise HTTPException(404,'market not found')
    except Exception as exc:raise HTTPException(502,f'smart-money flow unavailable: {exc}')
@app.get('/api/events')
async def events():
    try:return await service.event_feed()
    except Exception as exc:raise HTTPException(502,f'event feed unavailable: {exc}')
@app.get('/api/cross-market/anomalies')
async def cross_market_anomalies():return cross_market.find(await service.markets())
@app.get('/api/cross-market/graph-anomalies')
async def graph_anomalies():return await service.graph_anomalies()
@app.get('/api/smart-money/leaderboard')
async def smart_money_leaderboard(category:str='OVERALL',time_period:str='MONTH',limit:int=10):
    try:return await service.smart.leaderboard(category,time_period,limit)
    except Exception as exc:raise HTTPException(502,f'smart-money data unavailable: {exc}')
@app.get('/api/smart-money/traders/{wallet}')
async def smart_money_profile(wallet:str):
    try:return await service.trader_profile(wallet)
    except ValueError as exc:raise HTTPException(422,str(exc))
    except Exception as exc:raise HTTPException(502,f'trader profile unavailable: {exc}')
@app.get('/api/calibration/demo')
async def calibration_demo():return calibration_metrics([.18,.28,.36,.48,.57,.64,.72,.81],[0,0,1,0,1,1,1,1],bins=5)
@app.get('/api/calibration/history')
async def calibration_history():return service.historical_calibration()
@app.post('/api/calibration/resolve')
async def calibration_resolve(req:ResolveMarketRequest):return service.resolve(req.market_id,req.outcome)
@app.post('/api/calibration/sync')
async def calibration_sync(limit:int=100):
    try:return await service.sync_resolutions(min(max(limit,1),100))
    except Exception as exc:raise HTTPException(502,f'resolution sync unavailable: {exc}')
@app.get('/api/experiments')
async def experiment_list(limit:int=50):return experiments.list(limit)
@app.post('/api/experiments')
async def experiment_register(req:ExperimentRequest):return experiments.register(req)
@app.post('/api/experiments/demo-grid')
async def experiment_demo_grid():return experiments.run_demo_grid()
@app.post('/api/validation/gate')
async def validation_gate(req:ValidationGateRequest):return validator.evaluate(req)
@app.get('/api/live/preflight')
async def live_preflight():return await service.live.preflight()
@app.post('/api/live/orders')
async def live_order(req:LiveOrderRequest):
    decision,result=await service.live_order(req)
    if not decision.approved:raise HTTPException(422,detail=decision.model_dump())
    return {'risk':decision,'order':result}
@app.get('/api/auto/status')
async def auto_status():return auto_trader.status()
@app.post('/api/auto/run-once')
async def auto_run_once():return await auto_trader.run_once()
@app.post('/api/auto/start')
async def auto_start():return await auto_trader.start()
@app.post('/api/auto/stop')
async def auto_stop():return await auto_trader.stop()
@app.on_event('startup')
async def startup_auto():
    if settings.auto_trade_enabled:await auto_trader.start()
@app.on_event('shutdown')
async def shutdown_auto():await auto_trader.stop()
@app.get('/api/paper/account')
async def paper_account():return service.broker.account()
@app.post('/api/paper/orders')
async def paper_order(req:PaperOrderRequest):
    decision,trade=await service.paper_order(req)
    if not decision.approved:raise HTTPException(422,detail=decision.model_dump())
    return {'risk':decision,'trade':trade,'account':service.broker.account()}
@app.post('/api/backtest')
async def backtest(req:BacktestRequest):return backtester.run(req)
@app.post('/api/backtest/demo')
async def demo_backtest():
    req=BacktestRequest(points=[{'price':.40,'model_probability':.49,'available_liquidity':1000},{'price':.42,'model_probability':.52,'available_liquidity':800},{'price':.46,'model_probability':.54,'available_liquidity':700},{'price':.51,'model_probability':.55,'available_liquidity':900},{'price':.56,'model_probability':.56,'available_liquidity':1100},{'price':.59,'model_probability':.56,'available_liquidity':900},{'price':.57,'model_probability':.54,'available_liquidity':750}],position_pct=.12,min_edge=.05,execution_mode='conservative');return backtester.run(req)
web=ROOT/'web'
if web.exists():
    app.mount('/assets',StaticFiles(directory=web),name='assets')
    @app.get('/')
    async def root():return FileResponse(web/'index.html')
