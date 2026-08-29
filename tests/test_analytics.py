from polyquant.analytics import ModelAnalytics

def test_scorecards_group_model_and_category():
    rows=[{'model_probability':.8,'outcome':1,'direction':'YES','edge':.1,'confidence':.8,'model_version':'v1','category':'Crypto'},{'model_probability':.2,'outcome':0,'direction':'NO','edge':.1,'confidence':.7,'model_version':'v1','category':'Crypto'},{'model_probability':.6,'outcome':0,'direction':'YES','edge':.05,'confidence':.6,'model_version':'v2','category':'Politics'}]
    s=ModelAnalytics().scorecards(rows)
    assert s['overall']['samples']==3
    assert len(s['by_model'])==2 and len(s['by_category'])==2
    crypto=next(x for x in s['by_category'] if x['name']=='Crypto');assert crypto['direction_accuracy']==1.0
