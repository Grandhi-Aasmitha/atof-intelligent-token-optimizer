import json
import pytest
from fastapi.testclient import TestClient
from atof.api import app
from atof.control import ControlSettings, save_settings

@pytest.mark.parametrize("adapter,agent",[("jetbrains_openai","chatgpt"),("jetbrains_gemini","gemini")])
def test_jetbrains_owned_preparation(tmp_path,monkeypatch,adapter,agent):
    monkeypatch.setenv("ATOF_CONTROL_DB",str(tmp_path/"control.db"))
    monkeypatch.setenv("ATOF_ANALYTICS_ENABLED","1")
    monkeypatch.setenv("ATOF_ANALYTICS_DB",str(tmp_path/"history.db"))
    client=TestClient(app,base_url="http://127.0.0.1:8081")
    text="heartbeat ok\n"*150+"RuntimeError: database unavailable"
    body={"task":"Diagnose error","error_output":text}
    route="/v1/adapters/"+adapter+"/prepare"
    headers={"X-ATOF-Adapter":"1"}
    on=client.post(route,json=body,headers=headers)
    assert on.status_code==200
    result=on.json()
    assert result["report"]["agent"]==agent
    assert result["report"]["executed_features"]==["coding.error_context"]
    assert result["prepared_prompt_estimate"]<result["original_prompt_estimate"]
    assert json.loads(result["prompt"])["task"]==body["task"]
    save_settings(ControlSettings(enabled=False))
    off=client.post(route,json=body,headers=headers).json()
    assert json.loads(off["prompt"])=={"task":body["task"],"evidence":text}
    assert off["report"]["control_policy"]=="disabled"
    assert not off["report"]["executed_features"]
    assert client.post("/v1/adapters/intellij_copilot/prepare",json=body,headers=headers).status_code==409
    assert client.get("/v1/dashboard/state").json()["connection"]["status"]=="unverified"
