"""Opt-in metadata-only token analytics; not proof of provider savings."""
import os, json, sqlite3
from datetime import datetime, timezone
from pathlib import Path
from .reporting import applied_response

def db_path():
    if os.getenv("ATOF_ANALYTICS_ENABLED","0") != "1":
        return None
    return Path(os.getenv("ATOF_ANALYTICS_DB") or str(Path.home()/".atof"/"analytics-v1.sqlite3")).expanduser()

def connect(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(str(path),timeout=5)
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("""CREATE TABLE IF NOT EXISTS request_metrics (
      request_id TEXT PRIMARY KEY, timestamp_utc TEXT NOT NULL, agent TEXT NOT NULL,
      intent TEXT NOT NULL, transport TEXT NOT NULL, delivery_status TEXT NOT NULL,
      fidelity_status TEXT NOT NULL, before_estimate INTEGER NOT NULL,
      after_estimate INTEGER, reduction_estimate INTEGER, reduction_pct REAL,
      duration_ms REAL, provider_tokens_saved INTEGER, feature_outcomes_json TEXT NOT NULL)""")
    return conn

def record(response):
    path=db_path()
    if path is None: return False
    r=applied_response(response).report
    features=[{"id":d.feature_id,"status":d.status,"reason":d.reason} for d in r.decisions]
    with connect(path) as conn:
        conn.execute("INSERT OR IGNORE INTO request_metrics VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
          (r.request_id,datetime.now(timezone.utc).isoformat(),r.agent,r.intent,
           r.execution_transport,r.delivery_status,r.fidelity_status,
           r.original_estimated_tokens,r.optimized_estimated_tokens,
           r.estimated_reduction_tokens,r.estimated_reduction_percent,
           r.execution_duration_ms,None,json.dumps(features,separators=(",",":"))))
    return True

def history(limit=50):
    path=db_path()
    if path is None:
        return {"enabled":False,"records":[],"message":"Set ATOF_ANALYTICS_ENABLED=1 to enable local analytics"}
    if not path.is_file():return {"enabled":True,"records":[]}
    with connect(path) as conn:
        conn.row_factory=sqlite3.Row
        rows=conn.execute("SELECT * FROM request_metrics ORDER BY timestamp_utc DESC,request_id DESC LIMIT ?",(min(200,max(1,limit)),)).fetchall()
    records=[]
    for row in rows:
        item=dict(row)
        outcomes=json.loads(item.pop('feature_outcomes_json'))
        item['features'] = [f for f in outcomes if f.get('status') == 'executed'] if (item['after_estimate'] is not None and (item['reduction_estimate'] or 0) > 0) else []
        records.append(item)
    return {"enabled":True,"records":records}

def summary(limit=200):
    data=history(limit); rows=data["records"]
    eligible=[r for r in rows if r["reduction_estimate"] is not None and r["after_estimate"] is not None]
    before=sum(r["before_estimate"] for r in eligible)
    after=sum(r["after_estimate"] for r in eligible)
    outcomes={}
    for r in rows:
        for f in r["features"]:
            key=f["id"]+"::"+f["status"];outcomes[key]=outcomes.get(key,0)+1
    return {"enabled":data["enabled"],"total_requests":len(rows),
      "candidate_requests":len(eligible),
      "estimated_original_tokens":before if eligible else None,
      "estimated_optimized_tokens":after if eligible else None,
      "estimated_tokens_removed":max(0,before-after) if eligible else None,
      "estimated_reduction_percent":round(100*(before-after)/before,2) if before else None,
      "feature_outcomes":outcomes,"verified_provider_tokens_saved":None,
      "verified_provider_savings_available":False,"measurement_method":"local_heuristic_estimate",
      "note":"Only reducing candidates included. Not provider billed token savings."}
