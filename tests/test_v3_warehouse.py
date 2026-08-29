from polyquant.models import FeatureSnapshot,Market,Prediction
from polyquant.storage import Storage


def test_research_warehouse_roundtrip(tmp_path):
    db=Storage(str(tmp_path/'v3.db'))
    m=Market(id='m1',question='Will test happen?',yes_price=.4,no_price=.6,source='demo')
    f=FeatureSnapshot(market_id='m1',market_probability=.4,liquidity=1000,opportunity_score=50)
    p=Prediction(market_id='m1',market_probability=.4,raw_probability=.5,model_probability=.47,confidence=.7,edge=.07,direction='YES',components={'evidence_adjustment':.01})
    db.save_market_snapshot(m);db.save_feature_snapshot(f);db.save_prediction(p);db.save_evidence('m1','{"evidence_score":0.5}')
    history=db.research_history('m1')
    assert len(history['market'])==1
    assert history['predictions'][0]['payload']['components']['evidence_adjustment']==.01
    assert history['features'][0]['payload']['opportunity_score']==50
    exp=db.save_experiment('x','probability_edge',{'min_edge':.05},{'roi':.1},'test')
    assert db.experiments()[0]['id']==exp['id']
    stats=db.stats()
    assert stats['market_snapshots']==1 and stats['experiments']==1
