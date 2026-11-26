"""One command for local setup and launch. No global hooks or policy changes."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--copilot', action='store_true', help='Opt in to configuring Copilot MCP in this workspace')
    parser.add_argument('--workspace', type=Path, default=ROOT, help='Approved workspace for --copilot')
    parser.add_argument('--verify', action='store_true', help='Run regression tests and local verification before launch')
    parser.add_argument('--setup-only', action='store_true', help='Install/configure but do not start dashboard')
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args(argv)
    if sys.version_info < (3,11):
        parser.error('Python 3.11 or newer required')
    if not 1 <= args.port <= 65535:
        parser.error('Invalid port')
    venv = ROOT / '.venv'
    python = venv / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    def run(*command, **kwargs):
        subprocess.run([str(x) for x in command], cwd=ROOT, check=True, **kwargs)
    try:
        if not python.is_file():
            run(sys.executable, '-m', 'venv', venv)
        run(python, '-m', 'pip', 'install', '-e', '.[dev]')
        env = os.environ.copy()
        env['ATOF_ANALYTICS_ENABLED'] = '1'
        if args.copilot:
            run(python, '-m', 'atof.mcp_setup', '--agent', 'copilot', '--write-vscode',
                '--analytics', '--workspace', args.workspace.resolve())
            print('Copilot workspace configured. Start/approve MCP in the IDE; live discovery is not verified.', flush=True)
        if args.verify:
            run(python, '-m', 'pytest', '-q')
            run(python, '-m', 'atof.verify_platform')
            run(python, '-m', 'atof.mcp_smoke', '--agent', 'all')
            run(python, '-m', 'atof.premodel')
        if args.setup_only:
            print('ATOF setup complete.', flush=True)
            return 0
        print(f'Open http://127.0.0.1:{args.port}/dashboard (Ctrl+C to stop). Local metadata analytics enabled.', flush=True)
        run(python, '-m', 'uvicorn', 'atof.api:app', '--host', '127.0.0.1', '--port', args.port, env=env)
        return 0
    except KeyboardInterrupt:
        return 0
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f'ATOF setup/start failed: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
