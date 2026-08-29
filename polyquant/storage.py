from __future__ import annotations
import json, sqlite3
from datetime import datetime, timezone
from .models import Prediction, PaperTrade

class Storage:
    def __init__(self,path:str):
        self.path=path; self._init()
    def _conn(self): return sqlite3.connect(self.path)
    def _init(self):
        with self._conn() as c:
            c.execute("CREATE TABLE IF NOT EXISTS predictions (id INTEGER PRIMARY KEY, market_id TEXT, created_at TEXT, payload TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS paper_trades (id TEXT PRIMARY KEY, market_id TEXT, created_at TEXT, payload TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS live_trades (id INTEGER PRIMARY KEY AUTOINCREMENT, market_id TEXT, created_at TEXT, notional REAL, payload TEXT)")
    def save_prediction(self,p:Prediction):
        with self._conn() as c: c.execute("INSERT INTO predictions(market_id,created_at,payload) VALUES(?,?,?)",(p.market_id,p.created_at.isoformat(),p.model_dump_json()))
    def save_trade(self,t:PaperTrade):
        with self._conn() as c: c.execute("INSERT OR REPLACE INTO paper_trades VALUES(?,?,?,?)",(t.id,t.market_id,t.created_at.isoformat(),t.model_dump_json()))

    def save_live_trade(self, market_id:str, notional:float, created_at:str, payload:str):
        with self._conn() as c: c.execute("INSERT INTO live_trades(market_id,created_at,notional,payload) VALUES(?,?,?,?)",(market_id,created_at,notional,payload))
    def live_notional_since(self, since_iso:str, market_id:str|None=None)->float:
        with self._conn() as c:
            if market_id is None:
                row=c.execute("SELECT COALESCE(SUM(notional),0) FROM live_trades WHERE created_at>=?",(since_iso,)).fetchone()
            else:
                row=c.execute("SELECT COALESCE(SUM(notional),0) FROM live_trades WHERE created_at>=? AND market_id=?",(since_iso,market_id)).fetchone()
        return float(row[0] or 0.0)
