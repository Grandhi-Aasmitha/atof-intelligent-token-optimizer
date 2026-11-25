"""Normal reports contain applied features, not inventory or planning trace."""
import json
import sqlite3
from fastapi.testclient import TestClient
from atof.api import app
from atof.models import OptimizeRequest
from atof.service import optimize
from atof.reporting import applied_response
from atof.mcp_server import handle_rpc
from atof.analytics import history, summary
from atof.engines.base import EngineResult, PluginSpec
from atof.engines.registry import EngineRegistry
from atof.engines.generic import encode, restores
from atof.legacy.tokens import estimate_text


def sample():
    return {'task':'Diagnose error', 'error_output':'heartbeat ok\n'*150+'RuntimeError: database unavailable\n',
            'tool_output':'one unique result'}


def assert_applied(report, ids):
    assert report['executed_features'] == ids
    assert [d['feature_id'] for d in report['decisions']] == ids
    assert all(d['status'] == 'executed' for d in report['decisions'])
    assert all(s['feature_id'] in ids for s in report['stage_results'])
    assert all(s['feature_id'] in ids for s in report['fidelity_checks'])


def test_default_http_and_mcp_reports(monkeypatch, tmp_path):
    monkeypatch.setenv('ATOF_ANALYTICS_ENABLED','1')
    monkeypatch.setenv('ATOF_ANALYTICS_DB',str(tmp_path/'test.db'))
    client = TestClient(app)
    req = sample()
    r = client.post('/v1/optimize', json=req).json()['report']
    assert_applied(r, ['coding.error_context'])
    for agent in ('copilot','codex','claude'):
        rpc = handle_rpc({'jsonrpc':'2.0','id':1,'method':'tools/call',
                          'params':{'name':'atof_optimize','arguments':req}},agent)
        assert_applied(json.loads(rpc['result']['content'][0]['text'])['report'], ['coding.error_context'])
    assert_applied(client.post('/v1/optimize',json={**req,'optimization_enabled':False}).json()['report'], [])
    assert_applied(client.post('/v1/optimize',json={'task':'Hello'}).json()['report'], [])
    assert_applied(client.post('/v1/optimize',json={**req,'agent':'copilot'}).json()['report'], [])
    assert_applied(client.post('/v1/optimize',json={'task':'Review','feature_override':'future.not_implemented','context':'data'}).json()['report'], [])
    assert all(f['id']=='coding.error_context' and f['status']=='executed' for r in history()['records'] for f in r['features'])
    assert summary()['feature_outcomes'] == {'coding.error_context::executed':4}


def test_old_history_filtered_without_database_migration(monkeypatch,tmp_path):
    db=tmp_path/'old.db'
    monkeypatch.setenv('ATOF_ANALYTICS_ENABLED','1')
    monkeypatch.setenv('ATOF_ANALYTICS_DB',str(db))
    r=optimize(OptimizeRequest(**sample())).report
    with sqlite3.connect(db) as conn:
        row=[{'id':'coding.error_context','status':'executed','reason':'ok'},
             {'id':'agent.tool_output','status':'skipped','reason':'not_smaller'}]
        conn.execute('UPDATE request_metrics SET feature_outcomes_json=? WHERE request_id=?',(json.dumps(row),r.request_id))
    assert [x['id'] for x in history()['records'][0]['features']] == ['coding.error_context']
    assert summary()['feature_outcomes'] == {'coding.error_context::executed':1}


def test_future_registered_plugin_without_report_changes(monkeypatch):
    from atof import service
    class Future:
        feature_id='custom.future'
        spec=PluginSpec(feature_id,'context',99,validator=restores)
        def optimize(self,request):
            candidate=encode(request.context)
            return EngineResult(candidate,estimate_text(request.context),estimate_text(candidate))
    monkeypatch.setattr(service,'_engines',EngineRegistry([Future()]))
    r=TestClient(app).post('/v1/optimize',json={'task':'Read context','context':'status healthy\n'*100}).json()['report']
    assert_applied(r,['custom.future'])
    r=TestClient(app).post('/v1/optimize',json={'task':'Read context','context':'one line'}).json()['report']
    assert_applied(r,[])


def test_diagnostic_trace_is_not_destroyed():
    response=optimize(OptimizeRequest(**sample()))
    assert any(d.feature_id=='agent.tool_output' and d.status=='skipped' for d in response.report.decisions)
    view=applied_response(response)
    assert_applied(view.report.model_dump(),['coding.error_context'])
    assert len(response.report.decisions)>len(view.report.decisions)
