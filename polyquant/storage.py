from __future__ import annotations
import json,sqlite3,uuid
from datetime import datetime,timezone
from .models import FeatureSnapshot,Market,PaperSettlement,PaperTrade,Prediction

class Storage:
    def __init__(self,path:str):self.path=path;self._init()
    def _conn(self):c=sqlite3.connect(self.path);c.row_factory=sqlite3.Row;return c
    @staticmethod
    def _now():return datetime.now(timezone.utc).isoformat()
    def _init(self):
        with self._conn() as c:
            c.execute('CREATE TABLE IF NOT EXISTS predictions (id INTEGER PRIMARY KEY, market_id TEXT, created_at TEXT, payload TEXT)');c.execute('CREATE INDEX IF NOT EXISTS idx_predictions_market_time ON predictions(market_id,created_at)')
            c.execute('CREATE TABLE IF NOT EXISTS market_snapshots (id INTEGER PRIMARY KEY AUTOINCREMENT, market_id TEXT, created_at TEXT, yes_price REAL, no_price REAL, liquidity REAL, volume_24h REAL, payload TEXT)');c.execute('CREATE INDEX IF NOT EXISTS idx_market_snapshots_market_time ON market_snapshots(market_id,created_at)')
            c.execute('CREATE TABLE IF NOT EXISTS feature_snapshots (id INTEGER PRIMARY KEY AUTOINCREMENT, market_id TEXT, created_at TEXT, payload TEXT)');c.execute('CREATE INDEX IF NOT EXISTS idx_feature_snapshots_market_time ON feature_snapshots(market_id,created_at)')
            c.execute('CREATE TABLE IF NOT EXISTS paper_trades (id TEXT PRIMARY KEY, market_id TEXT, created_at TEXT, payload TEXT)');c.execute('CREATE TABLE IF NOT EXISTS paper_settlements (id TEXT PRIMARY KEY, market_id TEXT, created_at TEXT, payload TEXT)')
            c.execute('CREATE TABLE IF NOT EXISTS live_trades (id INTEGER PRIMARY KEY AUTOINCREMENT, market_id TEXT, created_at TEXT, notional REAL, payload TEXT)')
            c.execute('CREATE TABLE IF NOT EXISTS evidence_snapshots (id INTEGER PRIMARY KEY AUTOINCREMENT, market_id TEXT, created_at TEXT, payload TEXT)');c.execute('CREATE INDEX IF NOT EXISTS idx_evidence_market_time ON evidence_snapshots(market_id,created_at)')
            c.execute('CREATE TABLE IF NOT EXISTS resolutions (market_id TEXT PRIMARY KEY, outcome INTEGER NOT NULL, resolved_at TEXT NOT NULL)');c.execute('CREATE TABLE IF NOT EXISTS trader_profiles (wallet TEXT PRIMARY KEY, updated_at TEXT NOT NULL, payload TEXT NOT NULL)');c.execute('CREATE TABLE IF NOT EXISTS experiments (id TEXT PRIMARY KEY, name TEXT NOT NULL, strategy TEXT NOT NULL, created_at TEXT NOT NULL, config TEXT NOT NULL, metrics TEXT NOT NULL, notes TEXT NOT NULL)')
            c.execute('CREATE TABLE IF NOT EXISTS decision_audit (id TEXT PRIMARY KEY,created_at TEXT NOT NULL,market_id TEXT,prediction_id INTEGER,mode TEXT NOT NULL,action TEXT NOT NULL,request TEXT NOT NULL,risk TEXT NOT NULL,result_id TEXT)');c.execute('CREATE INDEX IF NOT EXISTS idx_decision_market_time ON decision_audit(market_id,created_at)')
            c.execute('CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY,value TEXT NOT NULL)')
    def paper_starting_cash(self,default:float):
        with self._conn() as c:
            row=c.execute("SELECT value FROM meta WHERE key='paper_starting_cash'").fetchone()
            if row:return float(row['value'])
            c.execute("INSERT INTO meta(key,value) VALUES('paper_starting_cash',?)",(str(float(default)),));return float(default)
    def save_market_snapshot(self,m):
        with self._conn() as c:c.execute('INSERT INTO market_snapshots(market_id,created_at,yes_price,no_price,liquidity,volume_24h,payload) VALUES(?,?,?,?,?,?,?)',(m.id,self._now(),m.yes_price,m.no_price,m.liquidity,m.volume_24h,m.model_dump_json()))
    def save_feature_snapshot(self,f):
        with self._conn() as c:c.execute('INSERT INTO feature_snapshots(market_id,created_at,payload) VALUES(?,?,?)',(f.market_id,self._now(),f.model_dump_json()))
    def save_prediction(self,p):
        with self._conn() as c:cur=c.execute('INSERT INTO predictions(market_id,created_at,payload) VALUES(?,?,?)',(p.market_id,p.created_at.isoformat(),p.model_dump_json()));return int(cur.lastrowid)
    def save_trade(self,t):
        with self._conn() as c:c.execute('INSERT OR REPLACE INTO paper_trades VALUES(?,?,?,?)',(t.id,t.market_id,t.created_at.isoformat(),t.model_dump_json()))
    def paper_trades(self):
        with self._conn() as c:rows=c.execute('SELECT payload FROM paper_trades ORDER BY created_at,id').fetchall()
        out=[]
        for r in rows:
            try:out.append(PaperTrade.model_validate_json(r['payload']))
            except Exception:pass
        return out
    def save_settlement(self,s):
        with self._conn() as c:c.execute('INSERT OR IGNORE INTO paper_settlements VALUES(?,?,?,?)',(s.id,s.market_id,s.created_at.isoformat(),s.model_dump_json()))
    def paper_settlements(self):
        with self._conn() as c:rows=c.execute('SELECT payload FROM paper_settlements ORDER BY created_at,id').fetchall()
        out=[]
        for r in rows:
            try:out.append(PaperSettlement.model_validate_json(r['payload']))
            except Exception:pass
        return out
    def settlement_exists(self,market_id):
        with self._conn() as c:return c.execute('SELECT 1 FROM paper_settlements WHERE market_id=? LIMIT 1',(market_id,)).fetchone() is not None
    def latest_marks(self):
        sql='SELECT m.market_id,m.yes_price,m.no_price FROM market_snapshots m JOIN (SELECT market_id,MAX(id) mid FROM market_snapshots GROUP BY market_id) x ON x.mid=m.id';marks={}
        with self._conn() as c:
            for r in c.execute(sql):marks[(r['market_id'],'YES')]=float(r['yes_price']);marks[(r['market_id'],'NO')]=float(r['no_price'])
        return marks
    def save_evidence(self,market_id,payload):
        with self._conn() as c:c.execute('INSERT INTO evidence_snapshots(market_id,created_at,payload) VALUES(?,?,?)',(market_id,self._now(),payload))
    def save_resolution(self,market_id,outcome):
        if outcome not in (0,1):raise ValueError('outcome must be 0 or 1')
        with self._conn() as c:c.execute('INSERT OR REPLACE INTO resolutions(market_id,outcome,resolved_at) VALUES(?,?,?)',(market_id,outcome,self._now()))
    def resolution_for(self,market_id):
        with self._conn() as c:r=c.execute('SELECT outcome,resolved_at FROM resolutions WHERE market_id=?',(market_id,)).fetchone()
        return {'outcome':'YES' if r['outcome']==1 else 'NO','resolved_at':r['resolved_at']} if r else None
    def resolution_rows(self):
        with self._conn() as c:rows=c.execute('SELECT market_id,outcome,resolved_at FROM resolutions ORDER BY resolved_at').fetchall()
        return [{'market_id':r['market_id'],'outcome':'YES' if r['outcome']==1 else 'NO','resolved_at':r['resolved_at']} for r in rows]
    def save_decision(self,market_id,prediction_id,mode,action,request,risk,result_id=None):
        did=str(uuid.uuid4())
        with self._conn() as c:c.execute('INSERT INTO decision_audit VALUES(?,?,?,?,?,?,?,?,?)',(did,self._now(),market_id,prediction_id,mode,action,json.dumps(request,ensure_ascii=False),json.dumps(risk,ensure_ascii=False),result_id))
        return did
    def decisions(self,limit=100):
        with self._conn() as c:rows=c.execute('SELECT * FROM decision_audit ORDER BY created_at DESC LIMIT ?',(max(1,min(limit,1000)),)).fetchall()
        out=[]
        for r in rows:
            try:out.append({'id':r['id'],'created_at':r['created_at'],'market_id':r['market_id'],'prediction_id':r['prediction_id'],'mode':r['mode'],'action':r['action'],'request':json.loads(r['request']),'risk':json.loads(r['risk']),'result_id':r['result_id']})
            except json.JSONDecodeError:pass
        return out
    def trade_audit(self,trade_id):
        with self._conn() as c:t=c.execute('SELECT payload FROM paper_trades WHERE id=?',(trade_id,)).fetchone();d=c.execute("SELECT * FROM decision_audit WHERE result_id=? AND mode='paper' ORDER BY created_at DESC LIMIT 1",(trade_id,)).fetchone()
        if not t:return None
        result={'trade':json.loads(t['payload']),'decision':None}
        if d:result['decision']={'id':d['id'],'created_at':d['created_at'],'market_id':d['market_id'],'prediction_id':d['prediction_id'],'action':d['action'],'request':json.loads(d['request']),'risk':json.loads(d['risk'])}
        return result
    def save_trader_profile(self,wallet,payload):
        with self._conn() as c:c.execute('INSERT OR REPLACE INTO trader_profiles(wallet,updated_at,payload) VALUES(?,?,?)',(wallet.lower(),self._now(),json.dumps(payload,ensure_ascii=False)))
    def trader_profile(self,wallet):
        with self._conn() as c:r=c.execute('SELECT updated_at,payload FROM trader_profiles WHERE wallet=?',(wallet.lower(),)).fetchone()
        if not r:return None
        try:return {'updated_at':r['updated_at'],**json.loads(r['payload'])}
        except json.JSONDecodeError:return None
    def save_experiment(self,name,strategy,config,metrics,notes=''):
        eid=str(uuid.uuid4());created=self._now()
        with self._conn() as c:c.execute('INSERT INTO experiments(id,name,strategy,created_at,config,metrics,notes) VALUES(?,?,?,?,?,?,?)',(eid,name,strategy,created,json.dumps(config,ensure_ascii=False),json.dumps(metrics,ensure_ascii=False),notes))
        return {'id':eid,'name':name,'strategy':strategy,'created_at':created,'config':config,'metrics':metrics,'notes':notes}
    def experiments(self,limit=50):
        with self._conn() as c:rows=c.execute('SELECT * FROM experiments ORDER BY created_at DESC LIMIT ?',(max(1,min(limit,200)),)).fetchall()
        out=[]
        for r in rows:
            try:out.append({'id':r['id'],'name':r['name'],'strategy':r['strategy'],'created_at':r['created_at'],'config':json.loads(r['config']),'metrics':json.loads(r['metrics']),'notes':r['notes']})
            except json.JSONDecodeError:pass
        return out
    def market_history(self,market_id,limit=240):
        with self._conn() as c:rows=c.execute('SELECT created_at,yes_price,no_price,liquidity,volume_24h FROM market_snapshots WHERE market_id=? ORDER BY id DESC LIMIT ?',(market_id,max(1,min(limit,5000)))).fetchall()
        return [dict(r) for r in reversed(rows)]
    def research_history(self,market_id,limit=100):
        n=max(1,min(limit,500))
        with self._conn() as c:preds=c.execute('SELECT created_at,payload FROM predictions WHERE market_id=? ORDER BY id DESC LIMIT ?',(market_id,n)).fetchall();feats=c.execute('SELECT created_at,payload FROM feature_snapshots WHERE market_id=? ORDER BY id DESC LIMIT ?',(market_id,n)).fetchall()
        def decode(rows):
            out=[]
            for r in rows:
                try:out.append({'created_at':r['created_at'],'payload':json.loads(r['payload'])})
                except json.JSONDecodeError:pass
            return list(reversed(out))
        return {'market_id':market_id,'market':self.market_history(market_id,n),'predictions':decode(preds),'features':decode(feats),'evidence':list(reversed(self.evidence_for(market_id,n)))}
    def calibration_pairs(self):rows=self.scorecard_rows();return [float(r['model_probability']) for r in rows],[int(r['outcome']) for r in rows]
    def scorecard_rows(self):
        sql='''SELECT p.payload prediction,r.outcome,m.payload market FROM predictions p JOIN resolutions r ON r.market_id=p.market_id JOIN (SELECT market_id,MAX(id) pid FROM predictions GROUP BY market_id) lp ON lp.pid=p.id LEFT JOIN market_snapshots m ON m.id=(SELECT MAX(m2.id) FROM market_snapshots m2 WHERE m2.market_id=p.market_id) ORDER BY p.id''';out=[]
        with self._conn() as c:
            for row in c.execute(sql):
                try:
                    p=json.loads(row['prediction']);m=json.loads(row['market']) if row['market'] else {};out.append({'market_id':p.get('market_id'),'question':m.get('question',''),'category':m.get('category','General'),'model_version':p.get('model_version','unknown'),'market_probability':float(p['market_probability']),'model_probability':float(p['model_probability']),'confidence':float(p.get('confidence',0)),'edge':float(p.get('edge',0)),'direction':p.get('direction','PASS'),'outcome':int(row['outcome']),'created_at':p.get('created_at')})
                except Exception:pass
        return out
    def prediction_dataset(self,limit=10000):
        n=max(1,min(limit,100000));sql='''SELECT p.payload prediction,r.outcome,m.payload market FROM predictions p LEFT JOIN resolutions r ON r.market_id=p.market_id LEFT JOIN market_snapshots m ON m.id=(SELECT MAX(m2.id) FROM market_snapshots m2 WHERE m2.market_id=p.market_id) ORDER BY p.id DESC LIMIT ?''';out=[]
        with self._conn() as c:rows=c.execute(sql,(n,)).fetchall()
        for row in reversed(rows):
            try:
                p=json.loads(row['prediction']);m=json.loads(row['market']) if row['market'] else {};out.append({'created_at':p.get('created_at'),'market_id':p.get('market_id'),'question':m.get('question',''),'category':m.get('category','General'),'model_version':p.get('model_version','unknown'),'market_probability':p.get('market_probability'),'raw_probability':p.get('raw_probability'),'model_probability':p.get('model_probability'),'confidence':p.get('confidence'),'edge':p.get('edge'),'direction':p.get('direction'),'outcome':row['outcome']})
            except Exception:pass
        return out
    def evidence_for(self,market_id,limit=20):
        with self._conn() as c:rows=c.execute('SELECT created_at,payload FROM evidence_snapshots WHERE market_id=? ORDER BY id DESC LIMIT ?',(market_id,max(1,min(limit,500)))).fetchall()
        out=[]
        for r in rows:
            try:out.append({'created_at':r['created_at'],'payload':json.loads(r['payload'])})
            except json.JSONDecodeError:pass
        return out
    def prune_research(self,keep_per_market=2000):
        keep=max(10,keep_per_market);deleted={}
        with self._conn() as c:
            for table in ('market_snapshots','feature_snapshots','predictions','evidence_snapshots'):
                total=0;markets=[r[0] for r in c.execute(f'SELECT DISTINCT market_id FROM {table}').fetchall()]
                for mid in markets:
                    ids=[r[0] for r in c.execute(f'SELECT id FROM {table} WHERE market_id=? ORDER BY id DESC LIMIT -1 OFFSET ?',(mid,keep)).fetchall()]
                    if ids:c.executemany(f'DELETE FROM {table} WHERE id=?',[(i,) for i in ids]);total+=len(ids)
                deleted[table]=total
        return deleted
    def stats(self):
        with self._conn() as c:
            names=('market_snapshots','feature_snapshots','predictions','evidence_snapshots','paper_trades','paper_settlements','decision_audit','live_trades','resolutions','trader_profiles','experiments');return {n:int(c.execute(f'SELECT COUNT(*) FROM {n}').fetchone()[0]) for n in names}
    def save_live_trade(self,market_id,notional,created_at,payload):
        with self._conn() as c:c.execute('INSERT INTO live_trades(market_id,created_at,notional,payload) VALUES(?,?,?,?)',(market_id,created_at,notional,payload))
    def live_notional_since(self,since_iso,market_id=None):
        with self._conn() as c:r=c.execute('SELECT COALESCE(SUM(notional),0) FROM live_trades WHERE created_at>=?'+(' AND market_id=?' if market_id else ''),(since_iso,market_id) if market_id else (since_iso,)).fetchone()
        return float(r[0] or 0)
