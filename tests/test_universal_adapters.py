import json
import pytest
from fastapi.testclient import TestClient
from atof.api import app
from atof.adapters import AgentAdapter, UnsupportedAdapter, adapter_for_mcp
from atof.adapter_policy import inventory
from atof.control import ControlSettings, save_settings
from atof.models import OptimizeRequest
from atof.service import optimize
from atof.analytics import history

@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("ATOF_CONTROL_DB", str(tmp_path/"control.db"))
    monkeypatch.setenv("ATOF_ANALYTICS_DB", str(tmp_path/"history.db"))
    monkeypatch.setenv("ATOF_ANALYTICS_ENABLED","1")

def sample():
    return OptimizeRequest(task="Diagnose error", error_output="heartbeat ok\n"*150+"RuntimeError: database unavailable")

@pytest.mark.parametrize("agent", ["copilot","codex","claude"])
def test_mcp_contract(agent):
    r=adapter_for_mcp(agent).tool(sample())
    assert r.report.agent==agent
    assert r.report.delivery_status=="mcp_tool_result_returned"
    assert r.report.executed_features==["coding.error_context"]

@pytest.mark.parametrize("adapter,agent", [("owned_local","custom_api"),("openai_api","chatgpt"),("gemini_api","gemini")])
def test_prepare_and_global_off(adapter,agent):
    a=AgentAdapter(adapter)
    on=a.prepare(sample())
    assert on.response.report.agent==agent
    assert on.response.report.executed_features==["coding.error_context"]
    assert on.prepared_prompt_estimate<on.original_prompt_estimate
    assert json.loads(on.prompt)["task"]==sample().task
    assert "RuntimeError: database unavailable" in json.loads(on.prompt)["evidence"]
    save_settings(ControlSettings(enabled=False))
    off=a.prepare(sample())
    assert json.loads(off.prompt)=={"task":sample().task,"evidence":sample().error_output}
    assert off.prepared_prompt_estimate==off.original_prompt_estimate
    assert not off.response.report.executed_features
    assert off.response.report.control_policy=="disabled"
    assert not off.public()["provider_savings_verified"]
    assert len(history()["records"])==2
    assert "heartbeat ok" not in json.dumps(history())

def test_dispatch_exact_once_and_failure():
    adapter=AgentAdapter("openai_api")
    calls=[]
    def sender(prompt):
        calls.append(prompt)
        return "answer"
    with pytest.raises(PermissionError):
        adapter.dispatch(sample(),sender)
    assert not calls
    r=adapter.dispatch(sample(),sender,authorized=True)
    assert r["answer"]=="answer" and len(calls)==1
    assert len(json.loads(calls[0])["evidence"])<len(sample().error_output)
    assert not r["model_consumption_verified"]
    def bad(prompt):
        calls.append(prompt)
        raise TimeoutError("private secret")
    r=adapter.dispatch(sample(),bad,authorized=True)
    assert len(calls)==2
    assert r["report"]["delivery_status"]=="owned_sender_failed"
    assert not r["report"]["executed_features"]
    assert r["report"]["estimated_reduction_tokens"] is None
    assert "private secret" not in str(r)
    assert len(history()["records"])==2

def test_native_and_spoofed_labels_not_authorized():
    assert all(not a["live_agent_verified"] for a in inventory())
    for ident in ("mcp_copilot","chatgpt_web","gemini_web","eclipse_copilot","unknown"):
        with pytest.raises(UnsupportedAdapter):
            AgentAdapter(ident).prepare(sample())
    for agent in ("copilot","codex","claude","chatgpt","gemini"):
        assert optimize(sample().model_copy(update={"agent":agent})).optimized_context is None
    with pytest.raises(ValueError):
        AgentAdapter("gemini_api").prepare(sample().model_copy(update={"agent":"chatgpt"}))

def test_owned_endpoint_and_dashboard():
    c=TestClient(app,base_url="http://127.0.0.1:8081")
    payload=sample().model_dump()
    headers={"X-ATOF-Adapter":"1"}
    assert c.post("/v1/adapters/openai_api/prepare",json=payload).status_code==403
    assert c.post("/v1/adapters/openai_api/prepare",json=payload,headers={**headers,"Origin":"https://example.org"}).status_code==403
    assert c.post("/v1/adapters/chatgpt_web/prepare",json=payload,headers=headers).status_code==409
    r=c.post("/v1/adapters/openai_api/prepare",json=payload,headers=headers)
    assert r.status_code==200
    result=r.json()
    assert result["report"]["delivery_status"]=="owned_payload_prepared"
    assert result["prompt_estimated_reduction"]>0
    assert not result["model_consumption_verified"]
    state=c.get("/v1/dashboard/state").json()
    assert state["selected"]["agent"]=="chatgpt"
    assert state["feature_counts"]["used"]==1
    assert state["connection"]["status"]=="unverified"
    assert "heartbeat ok" not in json.dumps(state)
    assert "gemini" in c.get("/v1/agents/capabilities").json()
    assert "Manual optimization test" not in c.get("/dashboard").text
