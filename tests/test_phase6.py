"""Phase 6 dashboard, optional metadata-only storage, reporting boundaries."""
import json
from fastapi.testclient import TestClient
from atof.api import app
from atof.models import OptimizeRequest
from atof.service import optimize
from atof.analytics import record,history,summary

client=TestClient(app)

def test_dashboard_is_rendered_and_caveated():
    r=client.get('/dashboard')
    assert r.status_code==200
    assert 'ATOF' in r.text and 'not provider-measured savings' in r.text
    assert 'Original tokens' in r.text and 'Optimized tokens' in r.text

def test_persistence_disabled_by_default(monkeypatch,tmp_path):
    monkeypatch.delenv('ATOF_ANALYTICS_ENABLED',raising=False)
    monkeypatch.setenv('ATOF_ANALYTICS_DB',str(tmp_path/'metrics.sqlite3'))
    response=optimize(OptimizeRequest(task='Hello'))
    assert record(response) is False
    assert not (tmp_path/'metrics.sqlite3').exists()
    assert history()['enabled'] is False

def test_enabled_history_stores_no_raw_input(monkeypatch,tmp_path):
    path=tmp_path/'metrics.sqlite3'
    monkeypatch.setenv('ATOF_ANALYTICS_ENABLED','1')
    monkeypatch.setenv('ATOF_ANALYTICS_DB',str(path))
    secret='DO_NOT_STORE_PRIVATE_TEXT'
    result=optimize(OptimizeRequest(task='Investigate '+secret,
        error_output='heartbeat ok\n'*140+'RuntimeError: '+secret+'\n'))
    assert result.optimized_context
    assert path.exists()
    assert secret.encode() not in path.read_bytes()
    rows=history()['records']
    assert len(rows)==1
    assert rows[0]['provider_tokens_saved'] is None
    assert rows[0]['agent']=='custom_api'
    assert rows[0]['features'][0]['id']=='coding.error_context'
    s=summary()
    assert s['candidate_requests']==1
    assert s['estimated_tokens_removed']>0
    assert s['verified_provider_tokens_saved'] is None

def test_duplicate_record_deduplicated(monkeypatch,tmp_path):
    monkeypatch.setenv('ATOF_ANALYTICS_ENABLED','1')
    monkeypatch.setenv('ATOF_ANALYTICS_DB',str(tmp_path/'metrics.sqlite3'))
    r=optimize(OptimizeRequest(task='Hello'))
    assert record(r) is True
    assert len(history()['records'])==1

def test_no_fabricated_savings_without_reduction(monkeypatch,tmp_path):
    monkeypatch.setenv('ATOF_ANALYTICS_ENABLED','1')
    monkeypatch.setenv('ATOF_ANALYTICS_DB',str(tmp_path/'metrics.sqlite3'))
    optimize(OptimizeRequest(task='Diagnose error',error_output='RuntimeError: bad'))
    s=summary()
    assert s['candidate_requests']==0
    assert s['estimated_tokens_removed'] is None
    assert s['estimated_reduction_percent'] is None

def test_history_endpoints(monkeypatch,tmp_path):
    monkeypatch.setenv('ATOF_ANALYTICS_ENABLED','1')
    monkeypatch.setenv('ATOF_ANALYTICS_DB',str(tmp_path/'metrics.sqlite3'))
    result=client.post('/v1/optimize',json={'task':'Analyze error',
      'error_output':'heartbeat ok\n'*140+'RuntimeError: failure'})
    assert result.status_code==200
    assert client.get('/health').json()['phase']==6
    assert len(client.get('/v1/analytics/history').json()['records'])==1
    assert client.get('/v1/analytics/summary').json()['candidate_requests']==1
    assert client.get('/v1/analytics/history?limit=bad').status_code==422

def test_agent_selection_not_http_interception(monkeypatch,tmp_path):
    monkeypatch.setenv('ATOF_ANALYTICS_ENABLED','1')
    monkeypatch.setenv('ATOF_ANALYTICS_DB',str(tmp_path/'metrics.sqlite3'))
    for agent in ('copilot','codex','claude'):
        result=optimize(OptimizeRequest(task='Analyze error',agent=agent,
          error_output='heartbeat ok\n'*140+'RuntimeError: failure'))
        assert result.optimized_context is None
        assert result.report.provider_tokens_saved is None
        assert result.report.decisions[0].status=='unsupported'
    assert summary()['candidate_requests']==0

def test_history_never_contains_prompt_or_log(monkeypatch,tmp_path):
    monkeypatch.setenv('ATOF_ANALYTICS_ENABLED','1')
    monkeypatch.setenv('ATOF_ANALYTICS_DB',str(tmp_path/'metrics.sqlite3'))
    optimize(OptimizeRequest(task='TOP SECRET PROMPT',error_output='RuntimeError: TOP SECRET CONTENT'))
    assert 'TOP SECRET' not in json.dumps(history())

def test_history_limit_clamps(monkeypatch,tmp_path):
    monkeypatch.setenv('ATOF_ANALYTICS_ENABLED','1')
    monkeypatch.setenv('ATOF_ANALYTICS_DB',str(tmp_path/'metrics.sqlite3'))
    assert client.get('/v1/analytics/history?limit=9999').status_code==200
