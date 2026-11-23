"""Generate an additive VS Code MCP config, or print setup commands.

No user-level Codex/Claude configuration is modified automatically.
"""
import argparse
import json
import sys
from pathlib import Path


def vscode_server(python_path: str, agent: str='copilot') -> dict:
    if agent not in ('copilot','codex','claude'):
        raise ValueError('Unsupported agent')
    return {'type':'stdio', 'command':str(Path(python_path).resolve()),
            'args':['-m','atof.mcp_server','--agent',agent]}


def write_vscode_config(workspace: str, python_path: str) -> Path:
    root=Path(workspace).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError('Workspace directory does not exist')
    target=root/'.vscode'/'mcp.json'
    existing=json.loads(target.read_text(encoding='utf-8')) if target.exists() else {}
    if not isinstance(existing,dict) or not isinstance(existing.get('servers',{}),dict):
        raise ValueError('Invalid existing MCP server registry')
    config=vscode_server(python_path)
    name='atof-copilot'
    if name in existing.get('servers',{}) and existing['servers'][name] != config:
        raise ValueError('Existing ATOF MCP entry differs: review it and remove or rename manually')
    existing.setdefault('servers',{})[name]=config
    target.parent.mkdir(parents=True,exist_ok=True)
    # No auto-overwrite on conflicts or malformed files.
    target.write_text(json.dumps(existing,indent=2)+'\n',encoding='utf-8')
    return target


def main(argv=None):
    parser=argparse.ArgumentParser(description='ATOF MCP setup helper')
    parser.add_argument('--agent',choices=('copilot','codex','claude'),required=True)
    parser.add_argument('--python',default=sys.executable)
    parser.add_argument('--workspace',default='.')
    parser.add_argument('--write-vscode',action='store_true')
    args=parser.parse_args(argv)
    if args.write_vscode:
        if args.agent != 'copilot':
            parser.error('--write-vscode currently supports Copilot only')
        try:
            print(f'Wrote: {write_vscode_config(args.workspace,args.python)}')
        except (ValueError,FileNotFoundError,json.JSONDecodeError) as e:
            parser.error(str(e))
    else:
        print(json.dumps({'servers':{'atof-'+args.agent:vscode_server(args.python,args.agent)}},indent=2))

if __name__=='__main__':
    main()
