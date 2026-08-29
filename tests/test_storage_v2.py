from polyquant.models import Prediction
from polyquant.storage import Storage


def test_resolved_calibration_uses_latest_prediction(tmp_path):
    s=Storage(str(tmp_path/"db.sqlite"))
    s.save_prediction(Prediction(market_id="m1",market_probability=.4,raw_probability=.55,model_probability=.55,confidence=.7,edge=.15,direction="YES"))
    s.save_prediction(Prediction(market_id="m1",market_probability=.45,raw_probability=.65,model_probability=.65,confidence=.8,edge=.20,direction="YES"))
    s.save_resolution("m1",1)
    probs,outcomes=s.calibration_pairs()
    assert probs == [.65]
    assert outcomes == [1]
