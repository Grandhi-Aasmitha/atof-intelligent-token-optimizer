import json
import pytest
from fastapi.testclient import TestClient

from atof.api import app
from atof.models import OptimizeRequest
from atof.premodel import (DeliveryReceipt, LocalReceiptReceiver, compare, deliver,
                           digest, fixture, integration_capabilities)


class CaptureReceiver:
    def __init__(self):
        self.prompts = []

    def deliver(self, prompt):
        self.prompts.append(prompt)
        return DeliveryReceipt(digest(prompt), digest(prompt))


def test_exact_downstream_payload_off_on():
    receiver = CaptureReceiver()
    request = fixture()
    result = compare(request, receiver, authorized=True, persist=False)
    off, on = map(json.loads, receiver.prompts)
    assert off["task"] == on["task"] == request.task
    assert off["evidence"] == request.error_output
    assert "RuntimeError: database unavailable" in on["evidence"]
    assert on["evidence"] != off["evidence"]
    assert len(on["evidence"]) < len(off["evidence"])
    assert result["full_prompt_estimated_reduction"] > 0
    assert result["on"]["report"]["delivery_status"] == "controlled_receiver_confirmed"
    assert result["on"]["report"]["executed_features"] == ["coding.error_context"]
    assert result["off"]["report"]["executed_features"] == []
    assert result["provider_savings_verified"] is False


def test_authorization_and_agent_label_cannot_bypass_policy():
    receiver = CaptureReceiver()
    with pytest.raises(PermissionError):
        deliver(fixture(), receiver, persist=False)
    with pytest.raises(ValueError):
        deliver(fixture().model_copy(update={"agent": "copilot"}), receiver,
                authorized=True, persist=False)
    assert receiver.prompts == []


def test_no_reduction_preserves_exact_task_and_evidence():
    receiver = CaptureReceiver()
    request = OptimizeRequest(task="Explain this", error_output="RuntimeError: x")
    result = deliver(request, receiver, authorized=True, persist=False)
    assert json.loads(receiver.prompts[0]) == {"task":request.task,"evidence":request.error_output}
    assert result["report"]["executed_features"] == []
    assert result["prompt_estimated_reduction"] == 0


def test_bad_receipt_or_transport_failure_no_false_savings():
    class Bad:
        def __init__(self):
            self.calls = 0

        def deliver(self, prompt):
            self.calls += 1
            return DeliveryReceipt(digest(prompt), "wrong-digest")
    receiver = Bad()
    result = compare(fixture(), receiver, authorized=True, persist=False)
    assert receiver.calls == 1
    assert not result["complete"]
    assert result["on"] is None
    assert result["off"]["report"]["delivery_status"] == "controlled_delivery_failed"
    assert result["full_prompt_estimated_reduction"] is None
    assert result["off"]["report"]["executed_features"] == []


def test_on_failure_clears_candidate_features():
    class Bad:
        def deliver(self, prompt):
            raise TimeoutError()
    result = deliver(fixture(), Bad(), authorized=True, persist=False)
    assert result["delivery"] is None
    assert result["report"]["executed_features"] == []
    assert result["report"]["estimated_reduction_tokens"] is None


def test_ba_order():
    receiver = CaptureReceiver()
    result = compare(fixture(), receiver, authorized=True, order="BA", persist=False)
    assert result["complete"]
    assert len(receiver.prompts[0]) < len(receiver.prompts[1])


def test_capability_inventory_never_claims_native_support():
    info = integration_capabilities()
    assert info["catalog_scope"] == 48
    assert all(not a["live_agent_verified"] for a in info["adapters"])
    assert not info["automatic_interception_verified"]


def test_dashboard_verification_and_single_history_record_per_arm(tmp_path,monkeypatch):
    monkeypatch.setenv("ATOF_ANALYTICS_ENABLED","1")
    monkeypatch.setenv("ATOF_ANALYTICS_DB",str(tmp_path/"metrics.sqlite"))
    client = TestClient(app)
    result = client.post("/v1/integrations/verify").json()
    assert result["passed"]
    history = client.get("/v1/analytics/history").json()["records"]
    assert len(history) == 2
    rows = {r["request_id"]:r for r in history}
    for arm in ("off","on"):
        report = result[arm]["report"]
        stored = rows[report["request_id"]]
        assert stored["delivery_status"] == report["delivery_status"]
        assert [f["id"] for f in stored["features"]] == report["executed_features"]
        assert stored["provider_tokens_saved"] is None
    assert "heartbeat ok" not in json.dumps(history)
    assert client.get("/v1/integrations/capabilities").status_code == 200
    assert "Run pre-model OFF / ON verification" in client.get("/dashboard").text


def test_provider_receiver_uses_exact_prompt_without_original_copy():
    from atof.benchmark import ProviderObservation
    from atof.premodel import ProviderReceiver
    class SpyProvider:
        def __init__(self):
            self.prompt = None
        def generate(self, prompt, required_terms):
            self.prompt = prompt
            return ProviderObservation(100, 10, None, 1, "output-hash", True, "mock_receipt")
    provider = SpyProvider()
    result = deliver(fixture(), ProviderReceiver(provider), authorized=True, persist=False)
    assert "heartbeat ok\\n" * 150 not in provider.prompt
    assert json.loads(provider.prompt)["task"] == fixture().task
    assert result["delivery"]["receiver_sha256"] is None
    assert result["report"]["delivery_status"] == "controlled_provider_response_returned"
    assert result["report"]["provider_usage"]["input_tokens"] == 100
    assert not result["model_consumption_verified"]
    assert not result["provider_savings_verified"]
