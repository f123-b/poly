from pathlib import Path
from polyquant.models import Market,Prediction
from polyquant.storage import Storage

def test_prediction_dataset_and_scorecard_rows(tmp_path:Path):
    s=Storage(str(tmp_path/'data.db'));m=Market(id='m',question='Q?',category='Test',yes_price=.4,no_price=.6,source='demo');s.save_market_snapshot(m);p=Prediction(market_id='m',market_probability=.4,raw_probability=.6,model_probability=.55,confidence=.8,edge=.15,direction='YES',model_version='test-v');s.save_prediction(p);s.save_resolution('m',1)
    rows=s.prediction_dataset();assert rows[0]['category']=='Test' and rows[0]['outcome']==1
    scored=s.scorecard_rows();assert scored[0]['model_version']=='test-v'
