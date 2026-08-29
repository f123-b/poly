from __future__ import annotations
import math
from collections import defaultdict
from .calibration import calibration_metrics

class ModelAnalytics:
    @staticmethod
    def _summary(rows:list[dict],name:str)->dict:
        if not rows:return {'name':name,'samples':0,'brier_score':None,'log_loss':None,'ece':None,'direction_accuracy':None,'average_edge':None,'average_confidence':None}
        ps=[float(r['model_probability']) for r in rows];ys=[int(r['outcome']) for r in rows];m=calibration_metrics(ps,ys,bins=min(10,max(2,int(math.sqrt(len(rows))))))
        decided=[r for r in rows if r.get('direction') in ('YES','NO')];correct=sum(1 for r in decided if (r['direction']=='YES' and r['outcome']==1) or (r['direction']=='NO' and r['outcome']==0))
        return {'name':name,'samples':len(rows),'brier_score':m.brier_score,'log_loss':m.log_loss,'ece':m.ece,'direction_accuracy':correct/len(decided) if decided else None,'decided_predictions':len(decided),'average_edge':sum(float(r.get('edge',0)) for r in rows)/len(rows),'average_confidence':sum(float(r.get('confidence',0)) for r in rows)/len(rows)}
    def scorecards(self,rows:list[dict])->dict:
        models=defaultdict(list);categories=defaultdict(list)
        for r in rows:models[r.get('model_version','unknown')].append(r);categories[r.get('category','General')].append(r)
        return {'overall':self._summary(rows,'overall'),'by_model':[self._summary(v,k) for k,v in sorted(models.items())],'by_category':sorted((self._summary(v,k) for k,v in categories.items()),key=lambda x:x['samples'],reverse=True)}
