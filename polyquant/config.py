from __future__ import annotations
from functools import lru_cache
from pydantic_settings import BaseSettings,SettingsConfigDict
class Settings(BaseSettings):
    model_config=SettingsConfigDict(env_prefix='POLYQUANT_',env_file='.env',extra='ignore')
    mode:str='auto';db_path:str='./polyquant.db';starting_cash:float=10_000.0;scan_limit:int=20;min_edge:float=0.05;min_confidence:float=0.60;max_spread:float=0.05;min_liquidity:float=1_000.0;max_single_market_pct:float=0.03;max_total_exposure_pct:float=0.50;fractional_kelly:float=0.25
    paper_fee_bps:float=0.0;paper_slippage_bps:float=5.0;auto_trade_enabled:bool=False;auto_interval_seconds:int=60;auto_order_notional:float=100.0;auto_max_trades_per_cycle:int=3;auto_allow_pyramiding:bool=False
    realtime_enabled:bool=True;realtime_prefer_sdk:bool=True;realtime_poll_seconds:float=5.0;realtime_stale_seconds:float=20.0;realtime_market_limit:int=20;realtime_book_refresh_limit:int=5
    maintenance_enabled:bool=True;maintenance_interval_seconds:int=3600;maintenance_resolution_sync:bool=True;maintenance_resolution_limit:int=100
    event_feed_url:str|None=None;evidence_max_adjustment:float=0.035;evidence_confidence_weight:float=0.08;history_limit:int=240;smart_money_demo:bool=False;snapshot_retention_per_market:int=2000
    live_execution_enabled:bool=False;live_risk_ack:str='';live_private_key:str='';live_deposit_wallet:str='';live_max_order_notional:float=10.0;live_max_market_notional:float=20.0;live_max_daily_notional:float=25.0
    llm_base_url:str|None=None;llm_api_key:str|None=None;llm_model:str|None=None
@lru_cache
def get_settings()->Settings:return Settings()
