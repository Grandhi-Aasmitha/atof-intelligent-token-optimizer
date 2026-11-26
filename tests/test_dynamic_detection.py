import pytest
from fastapi.testclient import TestClient
from atof.api import app
from atof.models import OptimizeRequest
from atof.detection import detect, verify_detection
from atof.engines.base import PluginSpec
from atof.engines.registry import EngineRegistry
from atof.service import optimize
from atof.reporting import applied_response


def test_unforced_catalog_fixtures(monkeypatch):
    monkeypatch.delenv("ATOF_ANALYTICS_ENABLED", raising=False)
    result = verify_detection()
    assert result["total"] == len(EngineRegistry().capabilities())
    assert result["passed"] == result["total"], result


def test_prompt_hints_are_not_evidence():
    request = OptimizeRequest(task="Why is my unit test failing? Review error log.")
    result = detect(request)
    assert set(result["missing_evidence"]) == {"test_output", "error_output"}
    assert not result["selected_features"]
    assert not optimize(request).optimized_context


def test_mixed_evidence_and_off():
    request = OptimizeRequest(task="Analyze failing tests and error log",
        test_output="test_ok PASSED\n"*130+"test_bad FAILED\nE AssertionError: wrong total\n",
        error_output="heartbeat healthy\n"*100+"RuntimeError: database failed\n")
    result = detect(request)
    assert set(result["selected_features"]) == {"coding.test_log", "coding.error_context"}
    assert not detect(request.model_copy(update={"optimization_enabled":False}))["selected_features"]
    response = applied_response(optimize(request))
    assert set(response.report.executed_features) == set(result["selected_features"])
    assert "AssertionError" in response.optimized_context
    assert "RuntimeError: database failed" in response.optimized_context


def test_relevance_changes_source_strategy_not_registry_order():
    request = OptimizeRequest(task="Find invoice total implementation", files=[
        {"path":"invoice.py","content":"def invoice_total(x): return x * 2\n"},
        {"path":"weather.py","content":'def forecast(): return "sunny"\n'*150}], token_budget=200)
    assert detect(request)["selected_features"] == ["coding.repository_retrieval"]
    assert optimize(request).report.executed_features == ["coding.repository_retrieval"]
    assert detect(request.model_copy(update={"task":"Explain function and dependencies"}))["selected_features"] == ["coding.code_context"]


def test_custom_plugin_predicates():
    class Plugin:
        def __init__(self, name, predicate):
            self.feature_id = name
            self.spec = PluginSpec(name, "context", 10, validator=lambda a,b: True,
                                   applicable=predicate)
    def broken(request):
        raise RuntimeError("private data")
    engines = EngineRegistry([Plugin("future.ok",lambda r: True),
                              Plugin("future.no",lambda r: False),
                              Plugin("future.bad",broken)])
    result = detect(OptimizeRequest(task="Summarize",context="text"),engines=engines)
    assert result["selected_features"] == ["future.ok"]
    assert "private data" not in str(result)
    assert {d["reason"] for d in result["decisions"]} >= {"plugin_not_applicable","applicability_check_failed"}


def test_detect_endpoint_no_execution_or_history(tmp_path, monkeypatch):
    monkeypatch.setenv("ATOF_ANALYTICS_ENABLED","1")
    monkeypatch.setenv("ATOF_ANALYTICS_DB",str(tmp_path/"metrics.db"))
    c=TestClient(app)
    payload={"task":"Debug error","error_output":"heartbeat ok\n"*150+"RuntimeError: fail"}
    r=c.post("/v1/detect",json=payload).json()
    assert r["selected_features"] == ["coding.error_context"]
    assert r["executed"] is False
    assert not (tmp_path/"metrics.db").exists()
    assert not c.post("/v1/detect",json={**payload,"agent":"copilot"}).json()["selected_features"]
    assert "Check automatic feature detection" in c.get("/dashboard").text
    assert "Manual optimization test" not in c.get("/dashboard").text
