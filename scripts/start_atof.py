"""One command for local setup and launch. No global hooks or policy changes."""
import argparse
import os
import socket
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_REVISION = "report-only-v2"


def require_free_port(port):
    """Fail clearly rather than leaving the browser on an older listener."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            sock.bind(('127.0.0.1', port))
        except OSError as exc:
            raise RuntimeError(
                f'Port {port} is already in use or unavailable. Stop your previous ATOF '
                f'server with Ctrl+C, or choose another port with --port 8081. '
                'No running process was stopped automatically.'
            ) from exc


def validate_dashboard_source():
    html = ROOT / 'src' / 'atof' / 'ui' / 'dashboard.html'
    source = html.read_text(encoding='utf-8')
    if (f'content="{DASHBOARD_REVISION}"' not in source or
            any(marker in source for marker in ('Test an optimization request',
                'Manual optimization test', 'Authorized evidence type', 'id="evidence"', 'id="task"'))):
        raise RuntimeError('Wrong dashboard revision in this checkout. Pull the latest feature branch in the correct repository.')
    return html



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
        dashboard_path = validate_dashboard_source()
        print(f'ATOF project: {ROOT}\nDashboard source: {dashboard_path}\nDashboard revision: {DASHBOARD_REVISION}', flush=True)
        if not args.setup_only:
            require_free_port(args.port)
        if not python.is_file():
            run(sys.executable, '-m', 'venv', venv)
        run(python, '-m', 'pip', 'install', '-e', '.[dev]')
        env = os.environ.copy()
        env['ATOF_ANALYTICS_ENABLED'] = '1'
        # Prefer this checkout over stale editable installs or other projects.
        env['PYTHONPATH'] = str(ROOT / 'src') + (os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
        run(python, '-c', "import sys; from pathlib import Path; import atof.api as a; "
            "expected = Path(sys.argv[1]).resolve(); actual = Path(a.__file__).resolve(); "
            "assert actual == expected, f'Wrong ATOF package: {actual}'; "
            "assert a.DASHBOARD_REVISION == sys.argv[2], 'Wrong dashboard revision'; "
            "print('Verified API source:', actual)", ROOT / 'src' / 'atof' / 'api.py', DASHBOARD_REVISION, env=env)
        if args.copilot:
            run(python, '-m', 'atof.mcp_setup', '--agent', 'copilot', '--write-vscode',
                '--analytics', '--workspace', args.workspace.resolve())
            print('Copilot workspace configured. Start/approve MCP in the IDE; live discovery is not verified.', flush=True)
        if args.verify:
            run(python, '-m', 'pytest', '-q')
            run(python, '-m', 'atof.verify_platform')
            run(python, '-m', 'atof.detection')
            run(python, '-m', 'atof.mcp_smoke', '--agent', 'all')
            run(python, '-m', 'atof.premodel')
        if args.setup_only:
            print('ATOF setup complete.', flush=True)
            return 0
        print(f'ATOF is starting. Open http://127.0.0.1:{args.port}/dashboard (Ctrl+C to stop). Local metadata analytics enabled. No live AI adapter verified by startup.', flush=True)
        run(python, '-m', 'uvicorn', 'atof.api:app', '--host', '127.0.0.1', '--port', args.port, '--app-dir', ROOT / 'src', env=env)
        return 0
    except KeyboardInterrupt:
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f'ATOF setup/start failed: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
