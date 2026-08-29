from __future__ import annotations
import sqlite3
from .models import Prediction, PaperTrade

class Storage:
    def __init__(self,path:str):
        self.path=path; self._init()
    def _conn(self): return sqlite3.connect(self.path)
    def _init(self):
        with self._conn() as c:
            c.execute("CREATE TABLE IF NOT EXISTS predictions (id INTEGER PRIMARY KEY, market_id TEXT, created_at TEXT, payload TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS paper_trades (id TEXT PRIMARY KEY, market_id TEXT, created_at TEXT, payload TEXT)")
    def save_prediction(self,p:Prediction):
        with self._conn() as c: c.execute("INSERT INTO predictions(market_id,created_at,payload) VALUES(?,?,?)",(p.market_id,p.created_at.isoformat(),p.model_dump_json()))
    def save_trade(self,t:PaperTrade):
        with self._conn() as c: c.execute("INSERT OR REPLACE INTO paper_trades VALUES(?,?,?,?)",(t.id,t.market_id,t.created_at.isoformat(),t.model_dump_json()))
