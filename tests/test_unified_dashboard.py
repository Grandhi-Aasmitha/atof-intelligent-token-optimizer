import json
import sys
from fastapi.testclient import TestClient
from atof.api import app
from atof.mcp_setup import write_vscode_config


def test_catalog_and_single_dashboard():
    c=TestClient(app)
    catalog=c.get('/v1/features').json()
    engines=c.get('/v1/engines').json()
    assert catalog['count']==len(catalog['features'])==48
    assert set(x['id'] for x in catalog['features'] if x['implemented'])=={x['feature_id'] for x in engines['engines']}
    html=c.get('/dashboard').text
    for label in ('View all 48 features','Features utilized','Run pre-model OFF / ON verification','Request history','Benchmark imports','Runtime required · Not executable','/v1/dashboard/state'):
        assert label in html


def test_matched_comparison_and_history(tmp_path,monkeypatch):
    monkeypatch.setenv('ATOF_ANALYTICS_ENABLED','1')
    monkeypatch.setenv('ATOF_ANALYTICS_DB',str(tmp_path/'metrics.sqlite'))
    c=TestClient(app)
    payload={'task':'Diagnose repeated error','error_output':'heartbeat ok\n'*150+'RuntimeError: database unavailable','tool_output':'unique line'}
    r=c.post('/v1/compare',json=payload).json()
    a,b=r['off']['report'],r['on']['report']
    assert a['executed_features']==a['decisions']==[]
    assert b['executed_features']==['coding.error_context']
    assert [d['feature_id'] for d in b['decisions']]==b['executed_features']
    assert a['original_estimated_tokens']==b['original_estimated_tokens']
    assert b['optimized_estimated_tokens']<a['original_estimated_tokens']
    assert 'RuntimeError: database unavailable' in r['on']['optimized_context']
    assert r['provider_savings_verified'] is False
    records={x['request_id']:x for x in c.get('/v1/analytics/history').json()['records']}
    assert records[a['request_id']]['features']==[]
    assert [f['id'] for f in records[b['request_id']]['features']]==b['executed_features']
    assert c.post('/v1/compare',json={**payload,'agent':'copilot'}).status_code==400


def test_nonreducing_comparison():
    r=TestClient(app).post('/v1/compare',json={'task':'Hello'}).json()
    assert r['on']['optimized_context'] is None
    assert r['on']['report']['executed_features']==[]


def test_setup_config_analytics_idempotent(tmp_path):
    folder=tmp_path/'.vscode'
    folder.mkdir()
    path=folder/'mcp.json'
    path.write_text(json.dumps({'servers':{'other':{'command':'other'}}}))
    write_vscode_config(str(tmp_path),sys.executable,analytics=True)
    first=json.loads(path.read_text())
    write_vscode_config(str(tmp_path),sys.executable,analytics=True)
    assert json.loads(path.read_text())==first
    assert first['servers']['other']=={'command':'other'}
    assert first['servers']['atof-copilot']['env']['ATOF_ANALYTICS_ENABLED']=='1'
