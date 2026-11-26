import json
from fastapi.testclient import TestClient
from atof.api import app
from atof.control import ControlSettings, save_settings, read_settings

def test_owned_vscode_preparation_and_switch(tmp_path, monkeypatch):
    monkeypatch.setenv("ATOF_CONTROL_DB",str(tmp_path/"control.db"))
    monkeypatch.setenv("ATOF_ANALYTICS_DB",str(tmp_path/"analytics.db"))
    monkeypatch.setenv("ATOF_ANALYTICS_ENABLED","1")
    c=TestClient(app,base_url="http://127.0.0.1:8081")
    task="Diagnose error"
    text="heartbeat ok\n"*150+"RuntimeError: database unavailable"
    data={"task":task,"error_output":text}
    headers={"X-ATOF-Adapter":"1"}
    route="/v1/adapters/vscode_copilot_model/prepare"
    on=c.post(route,json=data,headers=headers)
    assert on.status_code==200
    r=on.json()
    assert r["report"]["agent"]=="copilot"
    assert r["report"]["executed_features"]==["coding.error_context"]
    assert r["prepared_prompt_estimate"]<r["original_prompt_estimate"]
    assert json.loads(r["prompt"])["task"]==task
    assert not r["model_consumption_verified"]
    save_settings(ControlSettings(preferred_ide="eclipse",preferred_agent="codex"))
    assert c.put("/v1/control/enabled",json={"enabled":False}).status_code==403
    assert c.put("/v1/control/enabled",json={"enabled":False},headers={"X-ATOF-Control":"1"}).status_code==200
    off=c.post(route,json=data,headers=headers).json()
    assert json.loads(off["prompt"])=={"task":task,"evidence":text}
    assert not off["report"]["executed_features"]
    assert off["report"]["control_policy"]=="disabled"
    assert read_settings().preferred_ide=="eclipse"
    assert read_settings().preferred_agent=="codex"
    assert c.post("/v1/adapters/vscode_copilot/prepare",json=data,headers=headers).status_code==409
    assert c.get("/v1/dashboard/state").json()["connection"]["status"]=="unverified"
