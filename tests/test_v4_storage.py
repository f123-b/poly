from polyquant.storage import Storage
from polyquant.demo_data import DEMO_MARKETS

def test_prune_research_keeps_recent_rows(tmp_path):
    s=Storage(str(tmp_path/'v4.db'));m=DEMO_MARKETS[0]
    for _ in range(15):s.save_market_snapshot(m)
    deleted=s.prune_research(10);assert deleted['market_snapshots']==5;assert len(s.market_history(m.id,100))==10
