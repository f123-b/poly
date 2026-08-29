from __future__ import annotations
import json, sqlite3, uuid
from datetime import datetime, timezone
from .models import Prediction, PaperTrade, Market, FeatureSnapshot

class Storage:
    def __init__(self,path:str): self.path=path; self._init()
    def _conn(self):
        c=sqlite3.connect(self.path); c.row_factory=sqlite3.Row; return c
    def _init(self):
        with self._conn() as c:
            c.execute("CREATE TABLE IF NOT EXISTS predictions (id INTEGER PRIMARY KEY, market_id TEXT, created_at TEXT, payload TEXT)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_predictions_market_time ON predictions(market_id,created_at)")
            c.execute("CREATE TABLE IF NOT EXISTS paper_trades (id TEXT PRIMARY KEY, market_id TEXT, created_at TEXT, payload TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS live_trades (id INTEGER PRIMARY KEY AUTOINCREMENT, market_id TEXT, created_at TEXT, notional REAL, payload TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS evidence_snapshots (id INTEGER PRIMARY KEY AUTOINCREMENT, market_id TEXT, created_at TEXT, payload TEXT)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_evidence_market_time ON evidence_snapshots(market_id,created_at)")
            c.execute("CREATE TABLE IF NOT EXISTS resolutions (market_id TEXT PRIMARY KEY, outcome INTEGER NOT NULL, resolved_at TEXT NOT NULL)")
            c.execute("CREATE TABLE IF NOT EXISTS market_snapshots (id INTEGER PRIMARY KEY AUTOINCREMENT, market_id TEXT, created_at TEXT, yes_price REAL, no_price REAL, liquidity REAL, volume_24h REAL, payload TEXT)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_market_snapshots_market_time ON market_snapshots(market_id,created_at)")
            c.execute("CREATE TABLE IF NOT EXISTS feature_snapshots (id INTEGER PRIMARY KEY AUTOINCREMENT, market_id TEXT, created_at TEXT, opportunity_score REAL, spread REAL, payload TEXT)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_feature_snapshots_market_time ON feature_snapshots(market_id,created_at)")
            c.execute("CREATE TABLE IF NOT EXISTS prediction_snapshots (id INTEGER PRIMARY KEY AUTOINCREMENT, market_id TEXT, created_at TEXT, model_probability REAL, edge REAL, confidence REAL, model_version TEXT, payload TEXT)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_prediction_snapshots_market_time ON prediction_snapshots(market_id,created_at)")
            c.execute("CREATE TABLE IF NOT EXISTS trader_profiles (wallet TEXT PRIMARY KEY, updated_at TEXT, payload TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS experiments (id TEXT PRIMARY KEY, created_at TEXT, name TEXT, strategy TEXT, config TEXT, result TEXT)")
    @staticmethod
    def _now()->str: return datetime.now(timezone.utc).isoformat()
    def save_market_snapshot(self,m:Market):
        with self._conn() as c: c.execute("INSERT INTO market_snapshots(market_id,created_at,yes_price,no_price,liquidity,volume_24h,payload) VALUES(?,?,?,?,?,?,?)",(m.id,self._now(),m.yes_price,m.no_price,m.liquidity,m.volume_24h,m.model_dump_json()))
    def save_feature_snapshot(self,f:FeatureSnapshot):
        with self._conn() as c: c.execute("INSERT INTO feature_snapshots(market_id,created_at,opportunity_score,spread,payload) VALUES(?,?,?,?,?)",(f.market_id,self._now(),f.opportunity_score,f.spread,f.model_dump_json()))
    def save_prediction(self,p:Prediction):
        with self._conn() as c:
            c.execute("INSERT INTO predictions(market_id,created_at,payload) VALUES(?,?,?)",(p.market_id,p.created_at.isoformat(),p.model_dump_json()))
            c.execute("INSERT INTO prediction_snapshots(market_id,created_at,model_probability,edge,confidence,model_version,payload) VALUES(?,?,?,?,?,?,?)",(p.market_id,p.created_at.isoformat(),p.model_probability,p.edge,p.confidence,p.model_version,p.model_dump_json()))
    def save_trade(self,t:PaperTrade):
        with self._conn() as c: c.execute("INSERT OR REPLACE INTO paper_trades VALUES(?,?,?,?)",(t.id,t.market_id,t.created_at.isoformat(),t.model_dump_json()))
    def save_evidence(self,market_id:str,payload:str):
        with self._conn() as c: c.execute("INSERT INTO evidence_snapshots(market_id,created_at,payload) VALUES(?,?,?)",(market_id,self._now(),payload))
    def save_resolution(self,market_id:str,outcome:int):
        if outcome not in (0,1): raise ValueError("outcome must be 0 or 1")
        with self._conn() as c: c.execute("INSERT OR REPLACE INTO resolutions(market_id,outcome,resolved_at) VALUES(?,?,?)",(market_id,outcome,self._now()))
    def calibration_pairs(self)->tuple[list[float],list[int]]:
        sql="""SELECT p.payload,r.outcome FROM predictions p JOIN resolutions r ON r.market_id=p.market_id JOIN (SELECT market_id,MAX(id) AS latest_id FROM predictions GROUP BY market_id) latest ON latest.latest_id=p.id ORDER BY p.id"""
        probs=[]; outcomes=[]
        with self._conn() as c:
            for row in c.execute(sql):
                try: payload=json.loads(row["payload"]); probs.append(float(payload["model_probability"])); outcomes.append(int(row["outcome"]))
                except (KeyError,TypeError,ValueError,json.JSONDecodeError): continue
        return probs,outcomes
    def evidence_for(self,market_id:str,limit:int=20)->list[dict]:
        with self._conn() as c: rows=c.execute("SELECT created_at,payload FROM evidence_snapshots WHERE market_id=? ORDER BY id DESC LIMIT ?",(market_id,max(1,min(limit,100)))).fetchall()
        out=[]
        for row in rows:
            try: out.append({"created_at":row["created_at"],"payload":json.loads(row["payload"])})
            except json.JSONDecodeError: continue
        return out
    def research_history(self,market_id:str|None=None,limit:int=100)->dict:
        limit=max(1,min(limit,500)); where=" WHERE market_id=?" if market_id else ""; args=(market_id,limit) if market_id else (limit,)
        out={}
        with self._conn() as c:
            for name in ("market_snapshots","feature_snapshots","prediction_snapshots","evidence_snapshots"):
                rows=c.execute(f"SELECT market_id,created_at,payload FROM {name}{where} ORDER BY id DESC LIMIT ?",args).fetchall(); parsed=[]
                for row in rows:
                    try: payload=json.loads(row["payload"])
                    except json.JSONDecodeError: payload={}
                    parsed.append({"market_id":row["market_id"],"created_at":row["created_at"],"payload":payload})
                out[name]=parsed
        return out
    def save_trader_profile(self,wallet:str,payload:dict):
        with self._conn() as c: c.execute("INSERT OR REPLACE INTO trader_profiles(wallet,updated_at,payload) VALUES(?,?,?)",(wallet,self._now(),json.dumps(payload,ensure_ascii=False)))
    def trader_profiles(self,limit:int=50)->list[dict]:
        with self._conn() as c: rows=c.execute("SELECT wallet,updated_at,payload FROM trader_profiles ORDER BY updated_at DESC LIMIT ?",(max(1,min(limit,200)),)).fetchall()
        out=[]
        for r in rows:
            try: p=json.loads(r["payload"])
            except json.JSONDecodeError: p={}
            out.append({"wallet":r["wallet"],"updated_at":r["updated_at"],**p})
        return out
    def create_experiment(self,name:str,strategy:str,config:dict,result:dict|None=None)->dict:
        eid=str(uuid.uuid4()); created=self._now(); result=result or {}
        with self._conn() as c: c.execute("INSERT INTO experiments(id,created_at,name,strategy,config,result) VALUES(?,?,?,?,?,?)",(eid,created,name,strategy,json.dumps(config,ensure_ascii=False),json.dumps(result,ensure_ascii=False)))
        return {"id":eid,"created_at":created,"name":name,"strategy":strategy,"config":config,"result":result}
    def list_experiments(self,limit:int=50)->list[dict]:
        with self._conn() as c: rows=c.execute("SELECT * FROM experiments ORDER BY created_at DESC LIMIT ?",(max(1,min(limit,200)),)).fetchall()
        return [{"id":r["id"],"created_at":r["created_at"],"name":r["name"],"strategy":r["strategy"],"config":json.loads(r["config"]),"result":json.loads(r["result"])} for r in rows]
    def stats(self)->dict:
        names=("market_snapshots","feature_snapshots","prediction_snapshots","evidence_snapshots","paper_trades","live_trades","resolutions","trader_profiles","experiments")
        with self._conn() as c: return {name:int(c.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]) for name in names}
    def save_live_trade(self, market_id:str, notional:float, created_at:str, payload:str):
        with self._conn() as c: c.execute("INSERT INTO live_trades(market_id,created_at,notional,payload) VALUES(?,?,?,?)",(market_id,created_at,notional,payload))
    def live_notional_since(self,since_iso:str,market_id:str|None=None)->float:
        with self._conn() as c:
            row=c.execute("SELECT COALESCE(SUM(notional),0) FROM live_trades WHERE created_at>=?"+(" AND market_id=?" if market_id else ""),(since_iso,market_id) if market_id else (since_iso,)).fetchone()
        return float(row[0] or 0.0)
