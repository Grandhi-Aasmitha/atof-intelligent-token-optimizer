from fastapi.testclient import TestClient
from atof.api import app
from atof.control import set_enabled

def test_chat_tool_policy_and_history(tmp_path, monkeypatch):
    monkeypatch.setenv("ATOF_CONTROL_DB", str(tmp_path / "control.sqlite"))
    monkeypatch.setenv("ATOF_ANALYTICS_DB", str(tmp_path / "analytics.sqlite"))
    monkeypatch.setenv("ATOF_ANALYTICS_ENABLED", "1")
    client = TestClient(app, base_url="http://127.0.0.1:8081")
    url = "/v1/integrations/vscode-chat/optimize"
    payload = {"task":"Explain calculate_total", "files":[{"path":"cart.py","content":"def calculate_total(price, quantity):\n    return price * quantity\n"}]}
    assert client.post(url,json=payload).status_code == 403
    headers = {"X-ATOF-Adapter":"1"}
    set_enabled(False)
    off = client.post(url,json=payload,headers=headers)
    assert off.status_code == 200
    assert off.json()["report"]["control_policy"] == "disabled"
    assert not off.json()["report"]["executed_features"]
    set_enabled(True)
    on = client.post(url,json=payload,headers=headers)
    assert on.status_code == 200
    assert on.json()["report"]["agent"] == "copilot"
    assert on.json()["report"]["execution_transport"] == "vscode_chat_tool"
    assert on.json()["report"]["provider_tokens_saved"] is None
    records = client.get("/v1/analytics/history").json()["records"]
    assert len(records) == 2
    assert all("skip_reasons" in r for r in records)
