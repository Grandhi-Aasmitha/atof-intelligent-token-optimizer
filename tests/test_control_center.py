import json
import os
import subprocess
import sys
import pytest
from fastapi.testclient import TestClient
from atof.api import app
from atof.control import read_settings, save_settings, ControlSettings
from atof.models import OptimizeRequest
from atof.service import optimize
from atof.mcp_server import _call_tool

PAYLOAD = {"task":"Diagnose error", "error_output":"heartbeat ok\n"*150+"RuntimeError: database unavailable"}
HEADERS = {"X-ATOF-Control":"1", "Origin":"http://127.0.0.1:8080"}

@pytest.fixture
def local(tmp_path, monkeypatch):
    monkeypatch.setenv("ATOF_CONTROL_DB",str(tmp_path/"control.db"))
    monkeypatch.setenv("ATOF_ANALYTICS_ENABLED","1")
    monkeypatch.setenv("ATOF_ANALYTICS_DB",str(tmp_path/"metrics.db"))
    monkeypatch.delenv("ATOF_MCP_SMOKE_TEST",raising=False)
    return TestClient(app,base_url="http://127.0.0.1:8080")


def set_control(client, enabled, ide="eclipse", agent="copilot"):
    r=client.put("/v1/control",headers=HEADERS,json={"enabled":enabled,"preferred_ide":ide,"preferred_agent":agent})
    assert r.status_code==200, r.text
    return r.json()


def test_toggle_real_http_and_mcp(local):
    assert local.get("/v1/control").json()["settings"]["enabled"]
    assert local.post("/v1/optimize",json=PAYLOAD).json()["report"]["executed_features"]
    state=set_control(local,False)
    assert state["settings"]["preferred_ide"]=="eclipse"
    assert state["connection_verified"] is False
    off=local.post("/v1/optimize",json={**PAYLOAD,"optimization_enabled":True}).json()
    assert off["optimized_context"] is None
    assert off["report"]["control_policy"]=="disabled"
    assert not off["report"]["executed_features"]
    tool=json.loads(_call_tool("atof_optimize",PAYLOAD,"copilot")["content"][0]["text"])
    assert tool["optimized_context"] is None
    assert tool["report"]["control_policy"]=="disabled"
    assert not local.post("/v1/detect",json=PAYLOAD).json()["selected_features"]
    set_control(local,True)
    assert local.post("/v1/optimize",json=PAYLOAD).json()["report"]["executed_features"]
    assert not local.post("/v1/optimize",json={**PAYLOAD,"optimization_enabled":False}).json()["report"]["executed_features"]


def test_settings_persist_across_processes(local):
    set_control(local,False,"intellij","codex")
    result=subprocess.run([sys.executable,"-c",
        "from atof.control import read_settings; print(read_settings().model_dump_json())"],
        env=os.environ.copy(),capture_output=True,text=True,check=True)
    assert json.loads(result.stdout)=={"enabled":False,"preferred_ide":"intellij","preferred_agent":"codex"}


def test_control_rejects_untrusted_writes(local):
    body={"enabled":False}
    assert local.put("/v1/control",json=body).status_code==403
    assert local.put("/v1/control",headers={**HEADERS,"Origin":"https://example.org"},json=body).status_code==403
    assert local.put("/v1/control",headers={**HEADERS,"Host":"example.org"},json=body).status_code==403
    assert local.put("/v1/control",headers=HEADERS,json={"enabled":"false"}).status_code==422
    assert read_settings().enabled


def test_settings_corrupt_fail_closed(local,monkeypatch,tmp_path):
    bad=tmp_path/"bad.db"
    bad.write_text("not sqlite",encoding="utf-8")
    monkeypatch.setenv("ATOF_CONTROL_DB",str(bad))
    response=optimize(OptimizeRequest(**PAYLOAD))
    assert response.optimized_context is None
    assert response.report.control_policy=="settings_unavailable"
    assert not local.get("/v1/control").json()["available"]


def test_diagnostics_separate_from_normal_off(local):
    set_control(local,False)
    diagnostic=local.post("/v1/diagnostics/optimize",json=PAYLOAD).json()
    assert diagnostic["report"]["executed_features"]
    assert diagnostic["report"]["control_policy"]=="diagnostic"
    assert not local.post("/v1/optimize",json={**PAYLOAD,"source_kind":"synthetic_test"}).json()["report"]["executed_features"]
    assert local.post("/v1/integrations/verify").json()["passed"]
    assert read_settings().enabled is False


def test_dashboard_contains_control_not_manual_form(local):
    html=local.get("/dashboard").text
    for text in ("ATOF Control Center","preferred-ide","preferred-agent","control-on","control-off","View all 48 features"):
        assert text in html
    assert 'id="evidence"' not in html
    assert 'Manual optimization test' not in html
