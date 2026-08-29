from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field

class BookLevel(BaseModel): price: float; size: float
class OrderBook(BaseModel): token_id: str; bids:list[BookLevel]=Field(default_factory=list); asks:list[BookLevel]=Field(default_factory=list); timestamp:datetime=Field(default_factory=lambda:datetime.now(timezone.utc))
class Market(BaseModel):
    id:str; question:str; slug:str=""; condition_id:str|None=None; category:str="General"; end_date:datetime|None=None; active:bool=True; closed:bool=False; volume:float=0.0; volume_24h:float=0.0; liquidity:float=0.0; yes_price:float=0.5; no_price:float=0.5; yes_token_id:str|None=None; no_token_id:str|None=None; source:Literal["polymarket","demo"]="polymarket"
class FeatureSnapshot(BaseModel):
    market_id:str; market_probability:float; best_bid:float|None=None; best_ask:float|None=None; spread:float=0.0; bid_depth:float=0.0; ask_depth:float=0.0; orderbook_imbalance:float=0.0; liquidity:float=0.0; liquidity_score:float=0.0; volume_score:float=0.0; uncertainty_score:float=0.0; opportunity_score:float=0.0
class Prediction(BaseModel):
    market_id:str; market_probability:float; raw_probability:float; model_probability:float; confidence:float; edge:float; direction:Literal["YES","NO","PASS"]; model_version:str="quant-ensemble-v3"; components:dict[str,float]=Field(default_factory=dict); rationale:list[str]=Field(default_factory=list); created_at:datetime=Field(default_factory=lambda:datetime.now(timezone.utc))
class Opportunity(BaseModel): market:Market; features:FeatureSnapshot; prediction:Prediction
class RiskDecision(BaseModel): approved:bool; reasons:list[str]=Field(default_factory=list); max_notional:float=0.0; suggested_notional:float=0.0
class PaperOrderRequest(BaseModel): market_id:str; outcome:Literal["YES","NO"]="YES"; side:Literal["BUY","SELL"]="BUY"; notional:float=Field(gt=0)
class PaperTrade(BaseModel): id:str; market_id:str; outcome:Literal["YES","NO"]; side:Literal["BUY","SELL"]; price:float; shares:float; notional:float; fee:float; created_at:datetime=Field(default_factory=lambda:datetime.now(timezone.utc))
class PaperPosition(BaseModel): market_id:str; outcome:Literal["YES","NO"]; shares:float; avg_price:float; mark_price:float; market_value:float; unrealized_pnl:float
class PaperAccount(BaseModel): starting_cash:float; cash:float; equity:float; exposure:float; realized_pnl:float; unrealized_pnl:float; positions:list[PaperPosition]=Field(default_factory=list); trades:list[PaperTrade]=Field(default_factory=list)
class LiveOrderRequest(BaseModel): market_id:str; outcome:Literal["YES","NO"]; notional:float=Field(gt=0); confirmation:str
class ResolveMarketRequest(BaseModel): market_id:str; outcome:Literal["YES","NO"]
class ExperimentRequest(BaseModel): name:str=Field(min_length=1,max_length=120); strategy:str="probability_edge"; config:dict[str,Any]=Field(default_factory=dict); metrics:dict[str,float|int|None]=Field(default_factory=dict); notes:str=Field(default="",max_length=2000)
class BacktestPoint(BaseModel): price:float; model_probability:float; available_liquidity:float|None=Field(default=None,ge=0)
class BacktestRequest(BaseModel):
    points:list[BacktestPoint]=Field(min_length=3); starting_cash:float=10_000.0; min_edge:float=0.05; position_pct:float=0.05; fee_bps:float=0.0; slippage_bps:float=10.0; latency_bps:float=2.0; execution_mode:Literal["strict","conservative"]="conservative"; max_participation:float=Field(default=0.10,gt=0,le=1)
class BacktestResult(BaseModel):
    starting_cash:float; ending_equity:float; roi:float; max_drawdown:float; trades:int; win_rate:float; sharpe:float; equity_curve:list[float]; fees_paid:float=0.0; slippage_cost:float=0.0; turnover:float=0.0; partial_fills:int=0
class ValidationGateRequest(BaseModel):
    resolved_samples:int=0; paper_trades:int=0; brier_score:float|None=None; roi:float|None=None; max_drawdown:float|None=None; sharpe:float|None=None; min_resolved_samples:int=100; min_paper_trades:int=100; max_brier_score:float=0.24; min_roi:float=0.0; max_allowed_drawdown:float=0.10; min_sharpe:float=0.5
