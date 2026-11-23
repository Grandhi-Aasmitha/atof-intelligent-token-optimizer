"""Local stdio MCP server for ATOF: no filesystem reads, no network calls.

Implements the small JSON-RPC stdio subset used for initialize, ping, tool
listing and invocation. Writes one JSON object per stdout line. ATOF agents
provide ALL evidence explicitly; this process never accesses project files.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from pydantic import ValidationError
from .models import OptimizeRequest
from .service import optimize
from .agent_capabilities import capabilities, AGENTS

PROTOCOL_VERSION = '2025-06-18'
MAX_MESSAGE_BYTES = 1_000_000

_EVIDENCE_FILE = {
    'type': 'object',
    'properties': {
        'path': {'type':'string', 'description':'Display label only; no file will be read'},
        'content': {'type':'string', 'description':'Complete authorized source contents'},
    },
    'required': ['path','content'], 'additionalProperties': False
}

REQUEST_SCHEMA = {
    'type': 'object',
    'properties': {
        'task': {'type':'string','description':'What should be optimized and why'},
        'files': {'type':'array','items':_EVIDENCE_FILE,'description':'Authorized source content; paths alone do not grant file access'},
        'diff': {'type':'string','description':'Optional complete git diff text'},
        'test_output': {'type':'string','description':'Optional test runner output'},
        'error_output': {'type':'string','description':'Optional exception/diagnostic output'},
        'feature_override': {'type':'string','description':'Optional exact feature ID; cannot override eligibility checks'},
        'max_optimizers': {'type':'integer','minimum':1,'maximum':5},
        'token_budget': {'type':'integer','minimum':64},
    },
    'required': ['task'],
    'additionalProperties': False,
}

TOOL_DEFS = [
    {
        'name':'atof_capabilities',
        'description':'List currently supported ATOF optimization engines and actual integration limitations. Does not access files or invoke models.',
        'inputSchema': {'type':'object','properties':{},'additionalProperties':False},
    },
    {
        'name':'atof_analyze',
        'description':'Inspect supplied source, diff, test and error evidence; report only relevant optimization features without executing.',
        'inputSchema': REQUEST_SCHEMA,
    },
    {
        'name':'atof_optimize',
        'description':'Explicitly optimize caller-supplied authorized evidence. Returns optimized context candidate and report; NOT verified model-token savings. Do not use this tool if evidence is confidential and MCP client policy disallows its processing.',
        'inputSchema': REQUEST_SCHEMA,
    },
]


def _error(code: int, message: str, req_id: Any) -> dict:
    return {'jsonrpc':'2.0','id':req_id,'error':{'code':code,'message':message}}


def _reply(req_id: Any, result: dict) -> dict:
    return {'jsonrpc':'2.0','id':req_id,'result':result}


def _tool_result(value: dict, *, is_error: bool = False) -> dict:
    # Content is serialized once; emitting both content and structuredContent
    # duplicates evidence in some clients and inflates model context.
    return {'content':[{'type':'text','text':json.dumps(value, separators=(',', ':'), ensure_ascii=False)}],
            'isError': is_error}


def _call_tool(name: str, arguments: dict, agent: str) -> dict:
    if name == 'atof_capabilities':
        if arguments:
            return _tool_result({'error':'unexpected_arguments'}, is_error=True)
        return _tool_result(capabilities(agent))
    if name not in ('atof_analyze','atof_optimize'):
        return _tool_result({'error':'unknown_tool'}, is_error=True)
    try:
        # The MCP server, not an untrusted tool argument, sets agent identity
        # and authorizes the explicit-return transport. Agent identity here is
        # client configuration, not cryptographic client authentication.
        validated = OptimizeRequest.model_validate({
            **arguments,
            'agent':agent, 'delivery_mode':'return_payload',
            'execute': name == 'atof_optimize',
        })
    except (ValidationError, TypeError, ValueError):
        return _tool_result({'error':'invalid_optimization_request'}, is_error=True)
    try:
        response=optimize(validated, transport='mcp_explicit')
    except Exception:
        return _tool_result({'error':'internal_optimizer_error'},is_error=True)
    return _tool_result(response.model_dump(mode='json', exclude_none=False))


def handle_rpc(msg: Any, agent: str) -> dict | None:
    if not isinstance(msg,dict) or msg.get('jsonrpc') != '2.0':
        return _error(-32600,'Invalid Request',msg.get('id') if isinstance(msg,dict) else None)
    req_id=msg.get('id')
    if 'id' not in msg:
        # Notifications MUST NOT receive replies.
        return None
    method=msg.get('method')
    params=msg.get('params',{})
    if not isinstance(params,dict):
        return _error(-32602,'Invalid params',req_id)
    if method == 'initialize':
        return _reply(req_id,{
            'protocolVersion':PROTOCOL_VERSION,
            'capabilities':{'tools':{'listChanged':False}},
            'serverInfo':{'name':'atof-token-optimizer','version':'0.5.0'},
            'instructions':'ATOF tools require caller-supplied authorized evidence; results are candidates, not confirmed provider token savings.',
        })
    if method == 'ping':
        return _reply(req_id,{})
    if method == 'tools/list':
        return _reply(req_id,{'tools':TOOL_DEFS})
    if method == 'tools/call':
        if not isinstance(params.get('name'),str) or not isinstance(params.get('arguments',{}),dict):
            return _error(-32602,'Invalid params',req_id)
        return _reply(req_id,_call_tool(params['name'],params.get('arguments',{}),agent))
    return _error(-32601,'Method not found',req_id)


def serve(agent: str, stdin=None, stdout=None) -> None:
    stdin=stdin or sys.stdin
    stdout=stdout or sys.stdout
    for line in stdin:
        try:
            if len(line.encode('utf-8')) > MAX_MESSAGE_BYTES:
                reply=_error(-32600,'Message too large',None)
            else:
                try:
                    parsed=json.loads(line)
                except json.JSONDecodeError:
                    reply=_error(-32700,'Parse error',None)
                else:
                    reply=handle_rpc(parsed,agent)
            if reply is not None:
                stdout.write(json.dumps(reply,separators=(',',':'),ensure_ascii=False)+'\n')
                stdout.flush()
        except Exception:
            # No diagnostics or input content on stdout. Log generic status
            # only to stderr so the JSON-RPC stream remains usable.
            print('ATOF MCP internal processing error',file=sys.stderr)


def main(argv=None) -> None:
    parser=argparse.ArgumentParser(description='ATOF MCP stdio server')
    parser.add_argument('--agent',choices=('codex','copilot','claude'),required=True)
    args=parser.parse_args(argv)
    serve(args.agent)

if __name__=='__main__':
    main()
