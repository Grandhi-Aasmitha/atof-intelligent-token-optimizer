"""Opt-in metadata-only token analytics; not proof of provider savings."""
import os, json, sqlite3
from contextlib import closing
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
    conn.execute('CREATE TABLE IF NOT EXISTS request_provenance (request_id TEXT PRIMARY KEY, source_kind TEXT NOT NULL)')
    conn.execute('CREATE TABLE IF NOT EXISTS request_diagnostics (request_id TEXT PRIMARY KEY, control_policy TEXT NOT NULL, decisions_json TEXT NOT NULL)')
    conn.execute('CREATE TABLE IF NOT EXISTS client_receipts (request_id TEXT PRIMARY KEY, outcome TEXT NOT NULL)')
    return conn

def record(response):
    path=db_path()
    if path is None: return False
    r=(response.report if response.report.execution_transport == 'vscode_chat_tool' else applied_response(response).report)
    features=[{"id":d.feature_id,"status":d.status,"reason":d.reason} for d in r.decisions]
    with closing(connect(path)) as conn, conn:
        conn.execute("INSERT OR IGNORE INTO request_metrics VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
          (r.request_id,datetime.now(timezone.utc).isoformat(),r.agent,r.intent,
           r.execution_transport,r.delivery_status,r.fidelity_status,
           r.original_estimated_tokens,r.optimized_estimated_tokens,
           r.estimated_reduction_tokens,r.estimated_reduction_percent,
           r.execution_duration_ms,None,json.dumps(features,separators=(",",":"))))
        conn.execute("INSERT OR IGNORE INTO request_provenance VALUES (?,?)", (r.request_id, r.source_kind))
        raw = response.report
        # Only registry IDs, fixed decision codes and counts; never store source or prompts.
        trace = [{"id":d.feature_id,"status":d.status,"reason":d.reason,
                  "estimated_before":d.estimated_before,"estimated_after":d.estimated_after}
                 for d in raw.decisions if d.feature_id in _known_features()]
        conn.execute('INSERT OR IGNORE INTO request_diagnostics VALUES (?,?,?)',
                     (r.request_id, raw.control_policy, json.dumps(trace,separators=(',',':'))))
    return True

def _known_features():
    from .registry import FeatureRegistry
    return {f.id for f in FeatureRegistry().all()}

def client_receipt(request_id, outcome):
    """Local client-reported response, not a provider attestation or usage receipt."""
    if outcome not in ('model_response_returned','submission_unconfirmed'):
        raise ValueError('Invalid outcome')
    path = db_path()
    if path is None or not path.is_file():
        return False
    with closing(connect(path)) as conn, conn:
        row = conn.execute(
            "SELECT 1 FROM request_metrics m JOIN request_provenance p USING(request_id) "
            "WHERE m.request_id=? AND m.agent='copilot' AND m.transport='owned_adapter' "
            "AND m.delivery_status='owned_payload_prepared' AND p.source_kind='owned_adapter'",
            (request_id,)).fetchone()
        if row is None:
            return False
        conn.execute('INSERT OR IGNORE INTO client_receipts VALUES (?,?)',(request_id,outcome))
        return conn.execute('SELECT outcome FROM client_receipts WHERE request_id=?',(request_id,)).fetchone()[0] == outcome

def history(limit=50):
    path=db_path()
    if path is None:
        return {"enabled":False,"records":[],"message":"Set ATOF_ANALYTICS_ENABLED=1 to enable local analytics"}
    if not path.is_file():return {"enabled":True,"records":[]}
    with closing(connect(path)) as conn, conn:
        conn.row_factory=sqlite3.Row
        rows=conn.execute("SELECT m.*, COALESCE(p.source_kind, 'legacy_unknown') AS source_kind, d.control_policy, d.decisions_json, c.outcome AS client_reported_outcome FROM request_metrics m LEFT JOIN request_provenance p ON m.request_id=p.request_id LEFT JOIN request_diagnostics d ON m.request_id=d.request_id LEFT JOIN client_receipts c ON m.request_id=c.request_id ORDER BY m.timestamp_utc DESC,m.request_id DESC LIMIT ?",(min(200,max(1,limit)),)).fetchall()
    records=[]
    for row in rows:
        item=dict(row)
        outcomes=json.loads(item.pop('feature_outcomes_json'))
        stored = item.pop('decisions_json')
        item['feature_diagnostics'] = json.loads(stored) if stored is not None else None
        trace = item['feature_diagnostics'] if stored is not None else outcomes
        item['skip_reasons'] = [f for f in trace if f.get('status') != 'executed']
        candidate = item['after_estimate'] is not None and (item['reduction_estimate'] or 0) > 0
        if candidate:
            item['optimization_outcome'] = 'candidate_generated'
        elif item['control_policy'] in ('disabled','request_disabled','settings_unavailable'):
            item['optimization_outcome'] = item['control_policy']
        elif stored is None:
            item['optimization_outcome'] = 'legacy_diagnostics_unavailable'
        elif not trace:
            item['optimization_outcome'] = 'no_eligible_evidence_or_strategy'
        else:
            item['optimization_outcome'] = 'no_accepted_reduction' if any(f['status'] != 'failed' for f in trace) else 'optimizer_failed'
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
