from __future__ import annotations
from pydantic import BaseModel

class CalibrationMetrics(BaseModel):
    samples:int
    brier_score:float
    log_loss:float
    ece:float
    bins:list[dict]

def calibration_metrics(predictions:list[float], outcomes:list[int], bins:int=10)->CalibrationMetrics:
    import math
    if len(predictions)!=len(outcomes) or not predictions: raise ValueError('predictions/outcomes must be same non-zero length')
    ps=[max(1e-6,min(1-1e-6,float(p))) for p in predictions]; ys=[int(y) for y in outcomes]
    brier=sum((p-y)**2 for p,y in zip(ps,ys))/len(ps)
    logloss=-sum(y*math.log(p)+(1-y)*math.log(1-p) for p,y in zip(ps,ys))/len(ps)
    rows=[]; ece=0.0
    for i in range(bins):
        lo=i/bins; hi=(i+1)/bins; idx=[j for j,p in enumerate(ps) if lo<=p<(hi if i<bins-1 else hi+1e-9)]
        if not idx: continue
        conf=sum(ps[j] for j in idx)/len(idx); freq=sum(ys[j] for j in idx)/len(idx); weight=len(idx)/len(ps)
        ece+=weight*abs(conf-freq); rows.append({'range':[lo,hi],'count':len(idx),'mean_prediction':conf,'actual_frequency':freq})
    return CalibrationMetrics(samples=len(ps),brier_score=brier,log_loss=logloss,ece=ece,bins=rows)
