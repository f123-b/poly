import pytest
from polyquant.config import Settings
from polyquant.demo_data import DEMO_MARKETS
from polyquant.realtime import RealtimeMarketCache
from polyquant.service import QuantService

def test_market_prices_normalize_yes_no_and_book():
    m=DEMO_MARKETS[0];c=RealtimeMarketCache(20);c.register_markets([m]);c.update_quote(m.yes_token_id,best_bid=.68,best_ask=.72,last_price=.70);c.update_quote(m.no_token_id,last_price=.30);c.update_book(m.yes_token_id,[{'price':.68,'size':10}],[{'price':.72,'size':12}],.70);p=c.market_prices(m);assert abs(p['yes_price']-.7)<1e-9 and c.book(m.yes_token_id).asks[0].price==.72

@pytest.mark.asyncio
async def test_quant_service_prefers_fresh_realtime_cache(tmp_path):
    s=Settings(mode='demo',db_path=str(tmp_path/'q.db'),maintenance_enabled=False,realtime_enabled=False);svc=QuantService(s);m=DEMO_MARKETS[0];c=RealtimeMarketCache(20);c.register_markets([m]);c.update_quote(m.yes_token_id,best_bid=.68,best_ask=.72,last_price=.70);c.update_quote(m.no_token_id,last_price=.30);c.update_book(m.yes_token_id,[{'price':.68,'size':1000}],[{'price':.72,'size':1000}],.70);svc.realtime_cache=c;op=await svc.opportunity_for(m);assert abs(op.market.yes_price-.7)<1e-9;assert abs(op.features.best_bid-.68)<1e-9 and abs(op.features.best_ask-.72)<1e-9
