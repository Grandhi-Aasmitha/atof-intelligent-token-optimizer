from fastapi.testclient import TestClient
from atof.api import app

def client(tmp_path, monkeypatch):
    monkeypatch.setenv("ATOF_CONTROL_DB", str(tmp_path / "control.db"))
    monkeypatch.setenv("ATOF_ANALYTICS_DB", str(tmp_path / "analytics.db"))
    monkeypatch.setenv("ATOF_ANALYTICS_ENABLED", "1")
    return TestClient(app, base_url="http://127.0.0.1:8081")

HEADERS = {"X-ATOF-Adapter": "1"}

def test_source_tool_reduces_and_explains_no_candidate(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    route = "/v1/integrations/vscode-chat/optimize"
    short = "def total(): return 1\n"
    def call(source):
        return c.post(route, headers=HEADERS, json={"task":"Explain total and dependencies",
            "files":[{"path":"service.py","content":source}]}).json()
    small = call(short)
    assert small["optimized_context"] is None
    r = c.get("/v1/analytics/history").json()["records"][0]
    assert r["optimization_outcome"] == "no_accepted_reduction"
    assert any(d["id"] == "coding.code_context" for d in r["skip_reasons"])
    source = "def subtotal(items):\n    return sum(items)\n\ndef total(items):\n    return subtotal(items)\n"
    source += "".join(f"\ndef unrelated_{i}(): return {i}\n" for i in range(100))
    large = call(source)
    assert large["optimized_context"]
    assert "def subtotal" in large["optimized_context"]
    assert "def total" in large["optimized_context"]
    assert large["report"]["estimated_reduction_tokens"] > 0
    assert large["report"]["provider_tokens_saved"] is None

def test_client_receipt_is_scoped_and_advisory(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    p = c.post("/v1/adapters/vscode_copilot_model/prepare",headers=HEADERS,
        json={"task":"Diagnose error","error_output":"heartbeat ok\n"*150+"RuntimeError: database unavailable"}).json()
    data = {"request_id":p["report"]["request_id"],"outcome":"model_response_returned"}
    route = "/v1/integrations/vscode-owned/receipt"
    assert c.post(route,json=data).status_code == 403
    assert c.post(route,headers={**HEADERS,"Origin":"https://example.org"},json=data).status_code == 403
    receipt = c.post(route,headers=HEADERS,json=data).json()
    assert receipt["recorded"] and not receipt["provider_savings_verified"]
    assert c.post(route,headers=HEADERS,json=data).json()["recorded"]
    assert not c.post(route,headers=HEADERS,json={**data,"outcome":"submission_unconfirmed"}).json()["recorded"]
    selected = c.get("/v1/dashboard/state").json()["selected"]
    assert selected["client_reported_outcome"] == "model_response_returned"
    assert not selected["live_verified"]
    assert selected["provider_tokens_saved"] is None
    assert c.get("/v1/dashboard/state").json()["connection"]["status"] == "unverified"

def test_full_trace_does_not_change_applied_feature_contract(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    r = c.post("/v1/optimize",json={"task":"Diagnose error",
        "error_output":"heartbeat ok\n"*150+"RuntimeError: bad",
        "tool_output":"one unique result"}).json()["report"]
    assert [d["feature_id"] for d in r["decisions"]] == ["coding.error_context"]
    record = c.get("/v1/analytics/history").json()["records"][0]
    assert [d["id"] for d in record["features"]] == ["coding.error_context"]
    assert any(d["id"] == "agent.tool_output" for d in record["skip_reasons"])
    assert "heartbeat ok" not in str(record)
