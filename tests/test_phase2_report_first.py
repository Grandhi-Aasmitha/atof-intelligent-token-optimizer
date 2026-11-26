import json
from fastapi.testclient import TestClient
from atof.api import app
from atof.feature_state import feature_states
from atof.mcp_server import _call_tool


def test_catalog_states():
    states = feature_states()
    assert len(states) == 48
    assert sum(x["state"] == "available" for x in states) == 7
    assert sum(x["state"] == "planned" for x in states) == 41
    states = feature_states({"agent":"copilot","transport":"http_api"})
    assert sum(x["state"] == "unavailable_for_agent" for x in states) == 7
    states = feature_states({"agent":"custom_api","transport":"http_api",
        "features":[{"id":"coding.error_context","status":"executed"}]})
    assert [x["id"] for x in states if x["used"]] == ["coding.error_context"]


def test_report_first_and_test_isolation(tmp_path, monkeypatch):
    monkeypatch.setenv("ATOF_ANALYTICS_ENABLED","1")
    monkeypatch.setenv("ATOF_ANALYTICS_DB",str(tmp_path/"state.db"))
    client = TestClient(app)
    state = lambda: client.get("/v1/dashboard/state").json()
    assert state()["latest"] is None
    payload = {"task":"Diagnose error","error_output":"heartbeat ok\n"*150+"RuntimeError: database unavailable"}
    r = client.post("/v1/diagnostics/optimize",json=payload).json()
    assert r["report"]["source_kind"] == "developer_test"
    assert state()["latest"] is None
    spoof = client.post("/v1/optimize",json={**payload,"agent":"copilot","source_kind":"agent_tool"}).json()
    assert spoof["report"]["source_kind"] == "local_api"
    assert state()["latest"] is None
    check = client.post("/v1/integrations/verify").json()
    assert check["passed"]
    assert state()["latest"] is None
    tool = json.loads(_call_tool("atof_optimize",payload,"copilot")["content"][0]["text"])
    assert state()["latest"]["request_id"] == tool["report"]["request_id"]
    assert not state()["latest"]["live_verified"]
    assert state()["connection"]["status"] == "unverified"
    assert state()["feature_counts"]["used"] == 1
    selected = client.get("/v1/dashboard/state",params={"request_id":r["report"]["request_id"]}).json()
    assert selected["selected"]["source_kind"] == "developer_test"
    assert "heartbeat ok" not in json.dumps(selected)
    html = client.get("/dashboard").text
    assert html.index("ATOF — Optimization Report") < html.index("Advanced · Developer diagnostics")
    for removed in ("Manual optimization test", "Test an optimization request", "Agent for local test", "Authorized evidence type", "Load synthetic example", 'id="evidence"', 'id="task"', 'id="optimize"'):
        assert removed not in html
    assert "Run pre-model OFF / ON verification" in html
    assert "Run feature verification" in html
    assert '<details id="advanced">' in html


def test_smoke_records_do_not_become_latest(tmp_path,monkeypatch):
    monkeypatch.setenv("ATOF_ANALYTICS_ENABLED","1")
    monkeypatch.setenv("ATOF_ANALYTICS_DB",str(tmp_path/"smoke.db"))
    monkeypatch.setenv("ATOF_MCP_SMOKE_TEST","1")
    _call_tool("atof_optimize",{"task":"Explain","context":"line\n"*150},"codex")
    data=TestClient(app).get("/v1/dashboard/state").json()
    assert data["latest"] is None
    assert data["history"][0]["source_kind"] == "synthetic_test"


def test_legacy_record_is_not_live(tmp_path,monkeypatch):
    from atof.analytics import connect
    path=tmp_path/"legacy.db"
    monkeypatch.setenv("ATOF_ANALYTICS_ENABLED","1")
    monkeypatch.setenv("ATOF_ANALYTICS_DB",str(path))
    with connect(path) as conn:
        conn.execute("INSERT INTO request_metrics VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("old","2026-01-01T00:00:00Z","copilot","explanation","mcp_explicit",
             "mcp_tool_result_returned","passed",100,50,50,50,1,None,"[]"))
    state=TestClient(app).get("/v1/dashboard/state").json()
    assert state["latest"] is None
    assert state["history"][0]["source_kind"] == "legacy_unknown"
