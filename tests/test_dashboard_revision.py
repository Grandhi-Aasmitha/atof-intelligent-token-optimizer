from fastapi.testclient import TestClient
from atof.api import app, DASHBOARD_REVISION


def test_dashboard_revision_and_cache():
    client = TestClient(app)
    page = client.get('/dashboard')
    assert page.status_code == 200
    assert page.headers['X-ATOF-Dashboard-Revision'] == DASHBOARD_REVISION
    assert 'no-store' in page.headers['Cache-Control']
    assert client.get('/health').json()['dashboard_revision'] == DASHBOARD_REVISION
    assert f'content="{DASHBOARD_REVISION}"' in page.text
    for text in ('Test an optimization request', 'Manual optimization test',
                 'Authorized evidence type', 'id="task"', 'id="evidence"'):
        assert text not in page.text
    assert 'ATOF — Optimization Report' in page.text
    assert 'View all 48 features' in page.text
    assert 'Request history and comparison' in page.text


def test_launcher_detects_wrong_checkout_and_busy_port(tmp_path, monkeypatch):
    import importlib.util
    import socket
    from pathlib import Path
    import pytest

    source = Path(__file__).resolve().parents[1] / 'scripts' / 'start_atof.py'
    spec = importlib.util.spec_from_file_location('atof_launcher_test', source)
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    assert launcher.validate_dashboard_source().is_file()
    monkeypatch.setattr(launcher, 'ROOT', tmp_path)
    old = tmp_path / 'src' / 'atof' / 'ui' / 'dashboard.html'
    old.parent.mkdir(parents=True)
    old.write_text('Test an optimization request', encoding='utf-8')
    with pytest.raises(RuntimeError, match='Wrong dashboard revision'):
        launcher.validate_dashboard_source()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        with pytest.raises(RuntimeError, match='already in use or unavailable'):
            launcher.require_free_port(listener.getsockname()[1])
