import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from atof.api import app
from atof import browser
from atof.control import ControlSettings, save_settings

ROOT=Path(__file__).resolve().parents[1]
ORIGIN="http://127.0.0.1:8081"
HEADERS={"Origin":ORIGIN,"X-ATOF-Browser":"1","Sec-Fetch-Site":"same-origin"}
TEXT="heartbeat ok\n"*150+"RuntimeError: database unavailable"

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv("ATOF_CONTROL_DB",str(tmp_path/"control.db"))
    monkeypatch.setenv("ATOF_ANALYTICS_ENABLED","1")
    monkeypatch.setenv("ATOF_ANALYTICS_DB",str(tmp_path/"history.db"))
    for key in ("ATOF_BROWSER_API_ENABLED","ATOF_BROWSER_OPENAI_MODEL","ATOF_BROWSER_GEMINI_MODEL","OPENAI_API_KEY","GEMINI_API_KEY"):
        monkeypatch.delenv(key,raising=False)
    return TestClient(app,base_url=ORIGIN)

def configure(monkeypatch,provider):
    monkeypatch.setenv("ATOF_BROWSER_API_ENABLED","1")
    prefix=provider.upper()
    monkeypatch.setenv("ATOF_BROWSER_"+prefix+"_MODEL","approved-model")
    monkeypatch.setenv(prefix+"_API_KEY","test-secret")

def data(provider="openai"):
    return {"provider":provider,"task":"Diagnose error","evidence":TEXT,"consent":True}

def test_default_off_and_origin(client,monkeypatch):
    calls=[]
    monkeypatch.setattr(browser,"_post",lambda *a:calls.append(a))
    assert client.get("/v1/browser/status").json()["providers"]==[]
    assert client.post("/v1/browser/ask",json=data(),headers=HEADERS).status_code==403
    configure(monkeypatch,"openai")
    for headers in ({},{"Origin":"https://evil.example","X-ATOF-Browser":"1"},{"Origin":ORIGIN,"X-ATOF-Browser":"1","Sec-Fetch-Site":"cross-site"}):
        assert client.post("/v1/browser/ask",json=data(),headers=headers).status_code==403
    assert client.post("/v1/browser/ask",json={**data(),"consent":False},headers=HEADERS).status_code==403
    assert client.post("/v1/browser/ask",json={**data(),"model":"evil"},headers=HEADERS).status_code==422
    assert calls==[]
    assert "test-secret" not in client.get("/v1/browser/status").text

@pytest.mark.parametrize("provider",["openai","gemini"])
def test_single_prepared_input_off_on(client,monkeypatch,provider):
    configure(monkeypatch,provider)
    calls=[]
    def post(url,body,headers):
        calls.append((url,body,headers))
        if provider=="openai":
            return {"status":"completed","output":[{"type":"message","content":[{"type":"output_text","text":"Database unavailable"}]}]}
        return {"candidates":[{"finishReason":"STOP","content":{"parts":[{"text":"Database unavailable"}]}}]}
    monkeypatch.setattr(browser,"_post",post)
    on=client.post("/v1/browser/ask",json=data(provider),headers=HEADERS)
    assert on.status_code==200
    assert on.json()["sender_returned"]
    assert on.json()["report"]["executed_features"]==["coding.error_context"]
    assert on.json()["prepared_prompt_estimate"]<on.json()["original_prompt_estimate"]
    def prompt(body):
        return json.loads(body["input"] if provider=="openai" else body["contents"][0]["parts"][0]["text"])
    assert len(calls)==1
    reduced=prompt(calls[0][1])
    assert reduced["task"]=="Diagnose error"
    assert "RuntimeError: database unavailable" in reduced["evidence"]
    assert len(reduced["evidence"])<len(TEXT)
    save_settings(ControlSettings(enabled=False))
    off=client.post("/v1/browser/ask",json=data(provider),headers=HEADERS).json()
    assert len(calls)==2
    assert prompt(calls[1][1])=={"task":"Diagnose error","evidence":TEXT}
    assert not off["report"]["executed_features"]
    assert off["report"]["control_policy"]=="disabled"
    assert off["prepared_prompt_estimate"]==off["original_prompt_estimate"]
    assert not off["provider_savings_verified"]
    assert "test-secret" not in json.dumps(off)
    state=client.get("/v1/dashboard/state").json()
    assert state["connection"]["status"]=="unverified"
    assert TEXT not in json.dumps(state)

def test_failure_no_retry(client,monkeypatch):
    configure(monkeypatch,"openai")
    calls=[]
    def bad(*args):
        calls.append(args)
        raise TimeoutError("private-data")
    monkeypatch.setattr(browser,"_post",bad)
    r=client.post("/v1/browser/ask",json=data(),headers=HEADERS).json()
    assert len(calls)==1 and r["answer"] is None and not r["sender_returned"]
    assert not r["report"]["executed_features"]
    assert r["report"]["estimated_reduction_tokens"] is None
    assert "private-data" not in json.dumps(r)

def test_permission_free_manifest_and_csp(client):
    manifest=json.loads((ROOT/"ide/browser/manifest.json").read_text(encoding="utf-8"))
    assert manifest["manifest_version"]==3
    for field in ("permissions","host_permissions","content_scripts","background","externally_connectable","web_accessible_resources"):
        assert not manifest.get(field)
    page=client.get("/browser")
    assert page.status_code==200 and "frame-ancestors 'none'" in page.headers["Content-Security-Policy"]
    assert client.get("/browser/client.js").status_code==200
    assert 'id="task"' not in client.get("/dashboard").text
    assert client.post("/v1/adapters/chatgpt_web/prepare",json={"task":"test"},headers={"X-ATOF-Adapter":"1"}).status_code==409
