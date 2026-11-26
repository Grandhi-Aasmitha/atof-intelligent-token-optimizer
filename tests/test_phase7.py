"""Phase 7 explicit IDE endpoint integration."""
from pathlib import Path
from fastapi.testclient import TestClient
from atof.api import app

client=TestClient(app)
ROOT=Path(__file__).resolve().parents[1]

def test_selected_error_context_candidate():
    r=client.post('/v1/ide/optimize',json={'ide':'vscode','task':'Analyze error',
        'text':'heartbeat ok\n'*140+'RuntimeError: database unavailable',
        'evidence_kind':'error'})
    assert r.status_code==200
    data=r.json()
    assert data['optimized_context']
    assert 'RuntimeError: database unavailable' in data['optimized_context']
    assert data['report']['provider_tokens_saved'] is None
    assert any('Explicit IDE candidate only' in w for w in data['report']['warnings'])

def test_empty_selected_text_rejected():
    r=client.post('/v1/ide/optimize',json={'ide':'intellij','task':'Explain code','text':''})
    assert r.status_code==422

def test_agent_name_cannot_impersonate_ide():
    r=client.post('/v1/ide/optimize',json={'ide':'copilot','task':'Explain code','text':'hello'})
    assert r.status_code==422

def test_path_label_is_not_file_read_authorization():
    r=client.post('/v1/ide/optimize',json={'ide':'vscode','task':'Explain total',
        'text':'def total(): return 1\n','evidence_kind':'source','path_label':'/etc/passwd'})
    assert r.status_code==200
    assert 'root:x:' not in (r.json()['optimized_context'] or '')

def test_vscode_extension_explicit_only():
    source=(ROOT/'ide/vscode/extension.js').read_text()
    assert 'atof.optimizeSelection' in source
    assert 'onDidChangeTextDocument' not in source
    assert 'http://127.0.0.1:8081' in source
    assert 'showWarningMessage' in source

def test_intellij_requires_consent():
    source=(ROOT/'ide/intellij/src/main/java/dev/atof/OptimizeSelectionAction.java').read_text()
    assert 'showYesNoDialog' in source
    client=(ROOT/'ide/intellij/src/main/java/dev/atof/AtofClient.java').read_text()
    assert 'http://127.0.0.1:8081' in client
    assert 'new LocalTransport' in client
