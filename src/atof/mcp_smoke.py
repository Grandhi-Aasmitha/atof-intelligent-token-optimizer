"""Phase 5 local live-process MCP smoke test (all three agent configurations)."""
from __future__ import annotations
import argparse
import json
import subprocess
import sys


def check(agent: str) -> dict:
    sample = 'heartbeat ok\n' * 120 + 'RuntimeError: payment calculation failed\n'
    requests = [
        {'jsonrpc':'2.0','id':1,'method':'initialize','params':{
            'protocolVersion':'2025-06-18','clientInfo':{'name':'atof-smoke','version':'1'},'capabilities':{}}},
        {'jsonrpc':'2.0','method':'notifications/initialized'},
        {'jsonrpc':'2.0','id':2,'method':'tools/list','params':{}},
        {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{
            'name':'atof_optimize', 'arguments':{'task':'Explain repeated runtime error','error_output':sample}}},
    ]
    process=subprocess.run([sys.executable,'-m','atof.mcp_server','--agent',agent],
        input='\n'.join(json.dumps(item) for item in requests)+'\n',text=True,
        capture_output=True,timeout=20)
    if process.returncode:
        raise RuntimeError('MCP server process failed')
    events=[json.loads(line) for line in process.stdout.splitlines()]
    if [event.get('id') for event in events] != [1,2,3]:
        raise RuntimeError('MCP request/response sequence mismatch')
    tools={tool['name'] for tool in events[1]['result']['tools']}
    if tools != {'atof_capabilities','atof_analyze','atof_optimize'}:
        raise RuntimeError('MCP tools not discovered')
    result=json.loads(events[2]['result']['content'][0]['text'])
    report=result['report']
    if (not result['optimized_context'] or
        report['delivery_status'] != 'mcp_tool_result_returned' or
        report['agent'] != agent or
        report['provider_tokens_saved'] is not None):
        raise RuntimeError('MCP optimized result or report not valid')
    return {'agent':agent,'tools_discovered':len(tools),'executed_features':report['executed_features'],
            'estimated_reduction_tokens':report['estimated_reduction_tokens'],
            'delivery':report['delivery_status'],'provider_savings':'NOT VERIFIED'}


def main(argv=None):
    parser=argparse.ArgumentParser(description='ATOF MCP smoke test')
    parser.add_argument('--agent',choices=('copilot','codex','claude','all'),default='all')
    args=parser.parse_args(argv)
    for name in (('copilot','codex','claude') if args.agent=='all' else (args.agent,)):
        print(json.dumps(check(name),ensure_ascii=False))
    print('PASS — MCP discovery + invocation (local stdio); real agent/model use NOT VERIFIED')

if __name__=='__main__':
    main()
