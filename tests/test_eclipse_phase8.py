import json
from pathlib import Path
import xml.etree.ElementTree as ET
import pytest
from fastapi.testclient import TestClient
from atof.api import app
from atof.control import ControlSettings, save_settings

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize("adapter,agent",[("eclipse_openai","chatgpt"),("eclipse_gemini","gemini")])
def test_eclipse_owned_preparation(tmp_path,monkeypatch,adapter,agent):
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
    assert "RuntimeError: database unavailable" in json.loads(result["prompt"])["evidence"]
    assert result["model_consumption_verified"] is False
    save_settings(ControlSettings(enabled=False))
    off=client.post(route,json=body,headers=headers).json()
    assert json.loads(off["prompt"])=={"task":body["task"],"evidence":text}
    assert off["report"]["control_policy"]=="disabled"
    assert not off["report"]["executed_features"]
    assert client.post("/v1/adapters/eclipse_copilot/prepare",json=body,headers=headers).status_code==409
    assert client.get("/v1/dashboard/state").json()["connection"]["status"]=="unverified"
    assert "heartbeat ok" not in json.dumps(client.get("/v1/dashboard/state").json())

def test_eclipse_protocol_and_packaging_contract():
    # Keep the common plain-Java protocol copies aligned pending a shared Java library.
    source=ROOT/"ide/intellij/src/main/java/dev/atof"
    target=ROOT/"ide/eclipse/dev.atof.eclipse/src/dev/atof/eclipse"
    for name in ("LocalTransport.java","Evidence.java","AtofClient.java","ProviderSender.java"):
        expected=(source/name).read_text(encoding="utf-8").replace("package dev.atof;","package dev.atof.eclipse;").replace("jetbrains_openai","eclipse_openai").replace("jetbrains_gemini","eclipse_gemini")
        assert (target/name).read_text(encoding="utf-8")==expected
    root=ROOT/"ide/eclipse"
    for p in root.rglob("*.xml"):
        ET.parse(p)
    plugin=ET.parse(root/"dev.atof.eclipse/plugin.xml").getroot()
    view=plugin.find("./extension/view")
    assert view.attrib["class"]=="dev.atof.eclipse.ControlView"
    assert (target/"ControlView.java").is_file()
