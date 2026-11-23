"""End-to-end engine selection, transformation, API and safe-fallback coverage."""
import pytest
from fastapi.testclient import TestClient
from atof.api import app
from atof.engines.registry import EngineRegistry
from atof.engines.external import ExternalEngineAdapter, ExternalEngineUnavailable
from atof.models import OptimizeRequest
from atof.service import optimize

client = TestClient(app)

def req(**overrides):
    data = {'task':'Review and explain this evidence','agent':'custom_api'}
    data.update(overrides)
    return OptimizeRequest(**data)

def test_registry_is_extensible_and_deduplicated():
    registry = EngineRegistry()
    assert len(registry.capabilities()) == 5
    assert registry.supports('coding.code_context')
    assert not registry.supports('core.model_routing')
    with pytest.raises(ValueError, match='duplicate'):
        from atof.engines.native_code import NativeCodeContextEngine
        EngineRegistry([NativeCodeContextEngine(), NativeCodeContextEngine()])

def test_repository_retrieval_returns_focused_file():
    result = optimize(req(task='Find invoice total implementation', files=[
        {'path':'invoice.py','content':'def invoice_total(x): return x * 2\n'},
        {'path':'weather.py','content':'def forecast(): return "sunny"\n' * 150},
    ], feature_override='coding.repository_retrieval', token_budget=200))
    assert result.report.executed_feature == 'coding.repository_retrieval'
    assert 'invoice.py' in result.optimized_context
    assert 'weather.py' not in result.optimized_context
    assert result.report.provider_tokens_saved is None

def test_diff_compression_preserves_changes():
    diff='diff --git a/app.py b/app.py\n--- a/app.py\n+++ b/app.py\n@@ -1,6 +1,6 @@\n'
    diff += ' context\n' * 60 + '-old\n+new\n' + ' context\n' * 60
    result=optimize(req(task='Review my changes',diff=diff))
    assert result.report.executed_feature == 'coding.code_diff'
    assert '-old' in result.optimized_context and '+new' in result.optimized_context
    assert result.report.estimated_reduction_tokens > 0

def test_test_log_preserves_failed_assertions():
    lines = ''.join(f'test_ok_{i} PASSED\n' for i in range(100))
    result=optimize(req(task='Analyze failing tests',test_output=lines+'test_bad FAILED\nE AssertionError: wrong total\n'))
    assert result.report.executed_feature == 'coding.test_log'
    assert 'test_bad FAILED' in result.optimized_context
    assert 'AssertionError' in result.optimized_context

def test_error_context_folds_only_repeated_noise():
    log='heartbeat healthy\n'*60+'RuntimeError: database connection failed\n'
    result=optimize(req(task='Diagnose error',error_output=log))
    assert result.report.executed_feature == 'coding.error_context'
    assert 'RuntimeError: database connection failed' in result.optimized_context

def test_unsupported_copilot_never_dispatches():
    result=optimize(req(task='Fix error',error_output='RuntimeError: bad\n'*40,agent='copilot'))
    assert result.optimized_context is None
    assert result.report.decisions[0].status == 'unsupported'
    assert result.report.engine is None

def test_no_diff_input_and_override_cannot_bypass_evidence():
    result=optimize(req(task='Review this',feature_override='coding.code_diff'))
    assert result.optimized_context is None
    assert any(d.reason == 'override_not_eligible' for d in result.report.decisions)

def test_no_savings_no_false_positive():
    result=optimize(req(task='Analyze tests',test_output='E AssertionError: wrong\n'))
    assert result.optimized_context is None
    assert result.report.delivery_status == 'not_attempted'
    assert result.report.estimated_reduction_tokens is None

def test_engine_endpoint():
    response=client.get('/v1/engines')
    assert response.status_code == 200
    assert response.json()['count'] == 5
    assert response.json()['external_token_optimizer'] == 'not_installed_license_review_required'

def test_external_engine_fails_closed():
    with pytest.raises(ExternalEngineUnavailable):
        ExternalEngineAdapter('core.prompt').optimize(req())

def test_mixed_evidence_only_one_engine_selected():
    result=optimize(req(task='Fix failing test error',test_output='test_fail FAILED\nE AssertionError\n',error_output='RuntimeError: x\n'*20))
    assert sum(d.status in {'selected','executed'} for d in result.report.decisions) <= 1
    assert any(d.status=='applicable' for d in result.report.decisions)
