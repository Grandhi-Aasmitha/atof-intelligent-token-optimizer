"""Phase 5 real MCP stdio RPC, safe transport, and agent capability tests."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from atof.api import app
from atof.agent_capabilities import capabilities
from atof.mcp_server import TOOL_DEFS, handle_rpc, serve
from atof.mcp_setup import vscode_server, write_vscode_config
from atof.models import OptimizeRequest
from atof.service import optimize


def rpc(method, params=None, req_id=1):
    return {'jsonrpc': '2.0', 'id': req_id, 'method': method, 'params': params or {}}


def payload(result):
    return json.loads(result['result']['content'][0]['text'])


def sample_error():
    return {'task':'Analyze repeated backend error',
            'error_output': 'heartbeat ok\n' * 160 + 'RuntimeError: database unavailable\n'}


def test_all_agents_claim_explicit_not_automatic():
    for agent in ('codex','copilot','claude'):
        info = capabilities(agent)
        assert info['explicit_optimization_supported'] is True
        assert info['integration'] == 'explicit_mcp_stdio_tool'
        assert info['automatic_model_input_replacement_verified'] is False
        assert info['provider_token_savings_verified'] is False


def test_initialize_and_discovery():
    result=handle_rpc(rpc('initialize', {'protocolVersion':'2025-06-18',
                                      'capabilities':{},'clientInfo':{'name':'test','version':'1'}}), 'copilot')
    assert result['result']['capabilities']['tools']['listChanged'] is False
    assert result['result']['protocolVersion'] == '2025-06-18'
    tools=handle_rpc(rpc('tools/list'),'copilot')['result']['tools']
    assert {t['name'] for t in tools} == {'atof_capabilities','atof_analyze','atof_optimize'}
    assert all(t['inputSchema']['type']=='object' for t in tools)


def test_explicit_optimization_all_clients():
    for agent in ('codex','copilot','claude'):
        result=handle_rpc(rpc('tools/call',{'name':'atof_optimize','arguments':sample_error()}),agent)
        value=payload(result)
        assert value['optimized_context']
        assert 'RuntimeError: database unavailable' in value['optimized_context']
        report=value['report']
        assert report['agent']==agent
        assert report['execution_transport']=='mcp_explicit'
        assert report['delivery_status']=='mcp_tool_result_returned'
        assert report['estimated_reduction_tokens']>0
        assert report['provider_tokens_saved'] is None
        assert report['provider_usage'] is None
        assert report['executed_features']==['coding.error_context']


def test_http_agent_label_is_not_trusted_as_mcp_authorization():
    req=OptimizeRequest(**sample_error(),agent='copilot')
    result=optimize(req)
    assert result.optimized_context is None
    assert result.report.decisions[0].status=='unsupported'
    assert result.report.execution_transport=='http_api'
    response=TestClient(app).post('/v1/optimize',json=req.model_dump() | {'agent':'claude'})
    assert response.json()['optimized_context'] is None


def test_mcp_agent_config_cannot_be_spoofed_by_args():
    result=handle_rpc(rpc('tools/call',{'name':'atof_optimize',
                                       'arguments':sample_error() | {'agent':'custom_api','execute':False,
                                                                     'delivery_mode':'observe_only'}}),'codex')
    value=payload(result)
    assert value['report']['agent']=='codex'
    assert value['report']['delivery_status']=='mcp_tool_result_returned'


def test_analyze_returns_only_applicable_features_without_optimization():
    result=handle_rpc(rpc('tools/call',{'name':'atof_analyze','arguments':sample_error()}),'copilot')
    value=payload(result)
    assert value['optimized_context'] is None
    assert value['report']['executed_features']==[]
    assert value['report']['decisions'][0]['feature_id']=='coding.error_context'
    assert value['report']['decisions'][0]['status']=='applicable'


def test_missing_real_evidence_and_invalid_data_fail_closed():
    result=handle_rpc(rpc('tools/call',{'name':'atof_optimize','arguments':{'task':'Analyze error'}}),'copilot')
    value=payload(result)
    assert value['optimized_context'] is None
    assert not value['report']['decisions']
    bad=handle_rpc(rpc('tools/call',{'name':'atof_optimize','arguments':{'task':''}}),'copilot')
    assert bad['result']['isError'] is True
    assert 'invalid_optimization_request' in bad['result']['content'][0]['text']


def test_unknown_tool_methods_and_notifications():
    assert handle_rpc(rpc('whatever'),'claude')['error']['code']==-32601
    assert handle_rpc(rpc('tools/call',{'name':'unknown','arguments':{}}),'claude')['result']['isError']
    assert handle_rpc({'jsonrpc':'2.0','method':'notifications/initialized'},'claude') is None
    assert handle_rpc(rpc('ping'),'copilot')['result']=={}


def test_server_stdout_has_no_log_noise():
    text='\n'.join(json.dumps(x) for x in [rpc('initialize'),
                                           {'jsonrpc':'2.0','method':'notifications/initialized'},
                                           rpc('tools/list',req_id=2)])+'\n'
    output=io.StringIO()
    serve('codex',io.StringIO(text),output)
    lines=[json.loads(s) for s in output.getvalue().splitlines()]
    assert [x['id'] for x in lines]==[1,2]
    assert lines[1]['result']['tools'][0]['name']=='atof_capabilities'


def test_actual_python_process_stdio_handshake_and_tool_call():
    # Test not only the handler but discovery and invocation over real stdio.
    frames=[rpc('initialize',{'protocolVersion':'2025-06-18','capabilities':{},
                              'clientInfo':{'name':'pytest','version':'1.0'}}),
            {'jsonrpc':'2.0','method':'notifications/initialized'},
            rpc('tools/list',req_id=2),
            rpc('tools/call',{'name':'atof_optimize','arguments':sample_error()},req_id=3)]
    env=os.environ.copy()
    env['PYTHONPATH']=str(Path(__file__).resolve().parents[1] / 'src')
    run=subprocess.run([sys.executable,'-m','atof.mcp_server','--agent','copilot'],
                       input='\n'.join(map(json.dumps,frames))+'\n',capture_output=True,
                       text=True,timeout=15,env=env)
    assert run.returncode==0,run.stderr
    rows=[json.loads(line) for line in run.stdout.splitlines()]
    assert [x['id'] for x in rows]==[1,2,3]
    assert {t['name'] for t in rows[1]['result']['tools']} == {'atof_capabilities','atof_analyze','atof_optimize'}
    assert payload(rows[2])['report']['delivery_status']=='mcp_tool_result_returned'


def test_vscode_config_additive(tmp_path):
    folder=tmp_path/'.vscode'
    folder.mkdir()
    config=folder/'mcp.json'
    config.write_text(json.dumps({'servers':{'other-service':{'type':'stdio','command':'other','args':[]}}}),encoding='utf-8')
    path=write_vscode_config(str(tmp_path),sys.executable)
    assert path==config
    obj=json.loads(config.read_text())
    assert 'other-service' in obj['servers']
    assert obj['servers']['atof-copilot']['command']==str(Path(sys.executable).resolve())
    assert obj['servers']['atof-copilot']['args']==['-m','atof.mcp_server','--agent','copilot']
    # Idempotent for the same command.
    write_vscode_config(str(tmp_path),sys.executable)
    assert len(json.loads(config.read_text())['servers'])==2


def test_existing_unexpected_config_not_overwritten(tmp_path):
    folder=tmp_path/'.vscode'; folder.mkdir()
    config=folder/'mcp.json'
    config.write_text('{"servers":{"atof-copilot":{"type":"stdio","command":"other","args":[]}}}')
    with pytest.raises(ValueError,match='differs'):
        write_vscode_config(str(tmp_path),sys.executable)
    assert 'other' in config.read_text()


def test_http_capabilities_endpoint_matches_actual_limitations():
    response=TestClient(app).get('/v1/agents/capabilities')
    assert response.status_code==200
    assert response.json()['copilot']['automatic_model_input_replacement_verified'] is False
    assert response.json()['codex']['provider_token_savings_verified'] is False


def test_tool_listing_is_stable_and_not_48_schemas():
    assert len(TOOL_DEFS)==3
    assert all(tool['name'].startswith('atof_') for tool in TOOL_DEFS)
