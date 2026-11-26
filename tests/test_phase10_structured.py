import json
import pytest
from fastapi.testclient import TestClient
from atof.api import app
from atof.structured import StructuredRequest,optimize_structured,STRUCTURED_FEATURES
from atof.verify_structured import verify,fixtures
from atof.readiness import readiness,BLOCKERS
from atof.control import ControlSettings,save_settings

@pytest.fixture(autouse=True)
def isolated(tmp_path,monkeypatch):
    monkeypatch.setenv("ATOF_CONTROL_DB",str(tmp_path/"control.db"))
    monkeypatch.setenv("ATOF_ANALYTICS_ENABLED","1")
    monkeypatch.setenv("ATOF_ANALYTICS_DB",str(tmp_path/"analytics.db"))

def test_all_catalog_contracts():
    info=readiness()
    assert info["total"]==48
    assert info["counts"]=={"text_engine":7,"structured_candidate":12,"control":7,"runtime_required":22}
    assert set(BLOCKERS)=={x["id"] for x in info["features"] if x["readiness"]=="runtime_required"}
    assert {x[0] for x in fixtures()}==STRUCTURED_FEATURES

def test_all_structured_positive_off():
    result=verify()
    assert result["total"]==12 and result["passed"]==12,result

def test_authorization_and_required_items():
    req=StructuredRequest(task="keep",kind="retrieval",top_k=1,allow_pruning=True,
        items=[{"id":"a","text":"required "*100},{"id":"b","text":"required two "*100}])
    with pytest.raises(PermissionError):
        optimize_structured(req)
    req=req.model_copy(update={"authorized":True})
    r=optimize_structured(req)
    assert r["before"]==r["after"] and len(r["items"])==2

def test_history_latest_and_targets_preserved():
    req=StructuredRequest(task="history",kind="history",authorized=True,allow_pruning=True,
        items=[{"id":"a","text":"old "*100,"optional":True,"superseded_by":"b"},
               {"id":"b","text":"replacement","optional":True},
               {"id":"c","text":"current","optional":True,"superseded_by":"b"}])
    r=optimize_structured(req)
    assert [x["id"] for x in r["items"]]==["b","c"]

def test_idempotence_and_mapping():
    req=StructuredRequest(task="process",kind="duplicate_requests",authorized=True,allow_deduplication=True,
        items=[{"id":"1","text":"long exact request "*100},{"id":"2","text":"long exact request "*100}])
    assert not optimize_structured(req)["report"]["executed_features"]
    r=optimize_structured(req.model_copy(update={"idempotent_batch":True}))
    assert r["id_map"]=={"1":"1","2":"1"} and len(r["items"])==1
    assert not r["provider_savings_verified"]

def test_global_off_and_api_history():
    c=TestClient(app,base_url="http://127.0.0.1:8081")
    _,kwargs=fixtures()[0]
    req=StructuredRequest(task="Explain",authorized=True,**kwargs)
    route="/v1/structured/optimize"
    headers={"X-ATOF-Structured":"1"}
    assert c.post(route,json=req.model_dump()).status_code==403
    assert c.post(route,json=req.model_dump(),headers={**headers,"Origin":"https://evil.example"}).status_code==403
    r=c.post(route,json=req.model_dump(),headers=headers).json()
    assert r["report"]["executed_features"]==["core.prompt"]
    state=c.get("/v1/dashboard/state").json()
    assert state["feature_counts"]["used"]==1
    assert "Repeat this exact long input" not in json.dumps(state)
    save_settings(ControlSettings(enabled=False))
    off=c.post(route,json=req.model_dump(),headers=headers).json()
    assert off["before"]==off["after"] and off["report"]["control_policy"]=="disabled"
    assert not off["report"]["executed_features"]
    assert c.get("/v1/features/readiness").json()["total"]==48
    assert c.post("/v1/verification/structured").json()["passed"]==12
    assert 'id="task"' not in c.get("/dashboard").text
