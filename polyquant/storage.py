from __future__ import annotations
import json, sqlite3
from datetime import datetime, timezone
from .models import Prediction, PaperTrade

class Storage:
    def __init__(self,path:str):
        self.path=path; self._init()
    def _conn(self):
        c=sqlite3.connect(self.path)
        c.row_factory=sqlite3.Row
        return c
    def _init(self):
        with self._conn() as c:
            c.execute("CREATE TABLE IF NOT EXISTS predictions (id INTEGER PRIMARY KEY, market_id TEXT, created_at TEXT, payload TEXT)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_predictions_market_time ON predictions(market_id,created_at)")
            c.execute("CREATE TABLE IF NOT EXISTS paper_trades (id TEXT PRIMARY KEY, market_id TEXT, created_at TEXT, payload TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS live_trades (id INTEGER PRIMARY KEY AUTOINCREMENT, market_id TEXT, created_at TEXT, notional REAL, payload TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS evidence_snapshots (id INTEGER PRIMARY KEY AUTOINCREMENT, market_id TEXT, created_at TEXT, payload TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS resolutions (market_id TEXT PRIMARY KEY, outcome INTEGER NOT NULL, resolved_at TEXT NOT NULL)")
    def save_prediction(self,p:Prediction):
        with self._conn() as c: c.execute("INSERT INTO predictions(market_id,created_at,payload) VALUES(?,?,?)",(p.market_id,p.created_at.isoformat(),p.model_dump_json()))
    def save_trade(self,t:PaperTrade):
        with self._conn() as c: c.execute("INSERT OR REPLACE INTO paper_trades VALUES(?,?,?,?)",(t.id,t.market_id,t.created_at.isoformat(),t.model_dump_json()))
    def save_evidence(self,market_id:str,payload:str):
        with self._conn() as c: c.execute("INSERT INTO evidence_snapshots(market_id,created_at,payload) VALUES(?,?,?)",(market_id,datetime.now(timezone.utc).isoformat(),payload))
    def save_resolution(self,market_id:str,outcome:int):
        if outcome not in (0,1): raise ValueError("outcome must be 0 or 1")
        with self._conn() as c: c.execute("INSERT OR REPLACE INTO resolutions(market_id,outcome,resolved_at) VALUES(?,?,?)",(market_id,outcome,datetime.now(timezone.utc).isoformat()))
    def calibration_pairs(self)->tuple[list[float],list[int]]:
        sql="""
        SELECT p.payload,r.outcome
        FROM predictions p
        JOIN resolutions r ON r.market_id=p.market_id
        JOIN (
          SELECT market_id,MAX(id) AS latest_id FROM predictions GROUP BY market_id
        ) latest ON latest.latest_id=p.id
        ORDER BY p.id
        """
        probs=[]; outcomes=[]
        with self._conn() as c:
            for row in c.execute(sql):
                try:
                    payload=json.loads(row["payload"]); probs.append(float(payload["model_probability"])); outcomes.append(int(row["outcome"]))
                except (KeyError,TypeError,ValueError,json.JSONDecodeError):
                    continue
        return probs,outcomes
    def evidence_for(self,market_id:str,limit:int=20)->list[dict]:
        with self._conn() as c:
            rows=c.execute("SELECT created_at,payload FROM evidence_snapshots WHERE market_id=? ORDER BY id DESC LIMIT ?",(market_id,max(1,min(limit,100)))).fetchall()
        out=[]
        for row in rows:
            try: out.append({"created_at":row["created_at"],"payload":json.loads(row["payload"])})
            except json.JSONDecodeError: continue
        return out
    def save_live_trade(self, market_id:str, notional:float, created_at:str, payload:str):
        with self._conn() as c: c.execute("INSERT INTO live_trades(market_id,created_at,notional,payload) VALUES(?,?,?,?)",(market_id,created_at,notional,payload))
    def live_notional_since(self, since_iso:str, market_id:str|None=None)->float:
        with self._conn() as c:
            if market_id is None:
                row=c.execute("SELECT COALESCE(SUM(notional),0) FROM live_trades WHERE created_at>=?",(since_iso,)).fetchone()
            else:
                row=c.execute("SELECT COALESCE(SUM(notional),0) FROM live_trades WHERE created_at>=? AND market_id=?",(since_iso,market_id)).fetchone()
        return float(row[0] or 0.0)
