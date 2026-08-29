from polyquant.calibration import calibration_metrics

def test_calibration_metrics():
    r=calibration_metrics([.2,.4,.6,.8],[0,0,1,1],bins=5)
    assert 0 <= r.brier_score <= 1
    assert 0 <= r.ece <= 1
