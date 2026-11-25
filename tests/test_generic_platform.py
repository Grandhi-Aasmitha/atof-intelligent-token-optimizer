import json
import pytest
from fastapi.testclient import TestClient
from atof.api import app
from atof.engines.generic import encode, restores
from atof.engines.registry import EngineRegistry
from atof.engines.base import PluginSpec
from atof.models import OptimizeRequest
from atof.service import optimize
from atof.mcp_server import handle_rpc, REQUEST_SCHEMA
from atof.verify_platform import verify


def test_reversible_runs_and_marker_collision():
    for raw in ('OK\n'*100+'ERROR: unavailable', 'α\r\n'*100+'tail', 'a\n'*100+'b\n'*40):
        encoded = encode(raw)
        assert len(encoded) < len(raw)
        assert restores(raw, encoded)
        assert not restores(raw, encoded.replace('x100','x99'))
    raw = '[ATOF repeat x8]\nimportant\n'*20
    assert encode(raw) == raw
    assert not restores(raw, raw)
    assert not restores('x\n', '[ATOF repeat x999999]\nx\n')


def test_generic_plugins_compose_and_disabled_and_budget():
    req = OptimizeRequest(task='Explain', context='status healthy\n'*100+'Region: west\n',
                          tool_output='worker ready\n'*100+'ERROR: missing input\n', token_budget=64)
    result = optimize(req)
    assert set(result.report.executed_features) == {'core.context','agent.tool_output'}
    assert result.report.fidelity_status == 'passed'
    assert result.report.context_breakdown['context'] > 0
    assert result.report.budget_status in ('within_budget','over_budget')
    assert 'ERROR: missing input' in result.optimized_context
    disabled = optimize(req.model_copy(update={'optimization_enabled':False}))
    assert not disabled.optimized_context and not disabled.report.executed_features
    assert all(d.reason == 'optimization_disabled' for d in disabled.report.decisions)
    assert disabled.report.budget_status == 'over_budget'


def test_http_agent_cannot_bypass_transport_but_mcp_can():
    args = {'task':'Inspect tool output','tool_output':'worker ready\n'*100+'ERROR: bad\n'}
    assert 'tool_output' in REQUEST_SCHEMA['properties']
    for agent in ('copilot','codex','claude'):
        denied = optimize(OptimizeRequest(**args, agent=agent))
        assert denied.optimized_context is None
        rpc = handle_rpc({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'atof_optimize','arguments':args}},agent)
        report = json.loads(rpc['result']['content'][0]['text'])['report']
        assert report['executed_features'] == ['agent.tool_output']
        assert report['delivery_status'] == 'mcp_tool_result_returned'
        assert report['provider_tokens_saved'] is None


def test_unvalidated_plugin_rejected():
    class Bad:
        feature_id = 'custom.unknown'
        spec = PluginSpec(feature_id, 'context', 1)
    with pytest.raises(ValueError, match='validator'):
        EngineRegistry([Bad()])


def test_verification_matrix_and_dashboard_history(tmp_path, monkeypatch):
    monkeypatch.setenv('ATOF_ANALYTICS_ENABLED','1')
    monkeypatch.setenv('ATOF_ANALYTICS_DB',str(tmp_path/'verify.sqlite'))
    client = TestClient(app)
    result = client.post('/v1/verification').json()
    assert result['passed'] == result['total'] == 7
    assert result['provider_savings_verified'] is False
    history = client.get('/v1/analytics/history').json()['records']
    records = {r['request_id']:r for r in history}
    assert len(records) == 14
    for row in result['results']:
        record = records[row['request_id']]
        assert record['before_estimate'] == row['before']
        assert record['after_estimate'] == row['after']
        assert {'id':row['feature'],'status':'executed','reason':'optimized_candidate_composed'} in record['features']
    summary = client.get('/v1/analytics/summary').json()
    assert summary['total_requests'] == 14 and summary['candidate_requests'] == 7
    assert summary['estimated_tokens_removed'] == sum(r['removed'] for r in result['results'])
