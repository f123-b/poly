from polyquant.storage import Storage
from polyquant.demo_data import DEMO_MARKETS, demo_book
from polyquant.features import FeatureEngine
from polyquant.models import Prediction

def test_v3_snapshot_and_experiment(tmp_path):
    s=Storage(str(tmp_path/'v3.db')); m=DEMO_MARKETS[0]; f=FeatureEngine().compute(m,demo_book(m)); p=Prediction(market_id=m.id,market_probability=m.yes_price,raw_probability=.6,model_probability=.57,confidence=.7,edge=.1,direction='YES')
    s.save_market_snapshot(m); s.save_feature_snapshot(f); s.save_prediction(p); h=s.research_history(m.id)
    assert len(h['market_snapshots'])==1 and len(h['feature_snapshots'])==1 and len(h['prediction_snapshots'])==1
    e=s.create_experiment('baseline','probability_edge',{'min_edge':.05},{'roi':.01}); assert e['id']; assert s.list_experiments()[0]['name']=='baseline'
    stats=s.stats(); assert stats['market_snapshots']==1 and stats['experiments']==1
