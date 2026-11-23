"""Phase 4: fidelity, non-fabricated usage, measured estimates and API contracts."""
from fastapi.testclient import TestClient
from atof.api import app
from atof.fidelity import validate_stage
from atof.measurement import compare_context
from atof.models import OptimizeRequest
from atof.service import optimize
from atof.legacy.tokens import estimate_text, usage_counts
import pytest

client=TestClient(app)

def test_fidelity_detects_missing_added_diff_lines():
    original='diff --git a/a.py b/a.py\n-old\n+new\n unchanged\n'
    result=validate_stage('coding.code_diff',original,'diff --git a/a.py b/a.py\n-old\n unchanged\n')
    assert not result.passed
    assert result.reason == 'required_evidence_missing'
    assert result.anchors_checked == 2
    assert result.anchors_preserved == 1

def test_fidelity_retains_diff_changes():
    assert validate_stage('coding.code_diff','-old\n+new\n context','-old\n+new').passed

def test_fidelity_catches_dropped_failure():
    f=validate_stage('coding.test_log','test_bad FAILED\nE AssertionError: wrong total\nnoise', 'noise')
    assert not f.passed
    assert f.anchors_checked == 2

def test_fidelity_catches_dropped_exception():
    f=validate_stage('coding.error_context','RuntimeError: database unavailable\nnoise','noise')
    assert not f.passed

def test_fidelity_for_targeted_source_function():
    source='def total(items): return sum(items)\ndef unrelated(): return 1\n'
    assert not validate_stage('coding.code_context',source,'def unrelated(): return 1','Explain total').passed
    assert validate_stage('coding.code_context',source,'def total(items): return sum(items)','Explain total').passed

def test_fidelity_does_not_claim_semantic_equivalence():
    f=validate_stage('coding.code_diff',' context\n',' completely different')
    assert f.passed and f.anchors_checked == 0

def test_estimated_token_math_is_consistent():
    m=compare_context('A quick brown fox jumps over a lazy dog. '*50, 'short')
    assert m.original_tokens == estimate_text('A quick brown fox jumps over a lazy dog. '*50)
    assert m.reduction_tokens == m.original_tokens - m.optimized_tokens
    assert m.reduction_percent == round(100*m.reduction_tokens/m.original_tokens,2)
    assert m.method=='local_heuristic_estimate'

def test_empty_baseline_estimate_is_safe():
    m=compare_context('','')
    assert m.reduction_percent == 0.0

def test_api_exposes_measurement_limitations():
    r=client.get('/v1/reporting/capabilities')
    assert r.status_code==200
    assert r.json()['provider_usage']=='unavailable_no_provider_receipt'
    assert r.json()['fidelity'].startswith('conservative')

def test_optimize_uses_estimates_not_provider_usage():
    r=optimize(OptimizeRequest(task='Analyze error',error_output='heartbeat ok\n'*100+'RuntimeError: database failed\n'))
    assert r.optimized_context
    report=r.report
    assert report.provider_tokens_saved is None
    assert report.provider_usage is None
    assert report.measurement_method=='local_heuristic_estimate'
    assert report.estimated_reduction_percent is not None
    assert report.fidelity_status == 'passed'
    assert report.execution_duration_ms is not None and report.execution_duration_ms >= 0
    assert report.fidelity_checks

def test_real_api_response_reporting_fields():
    body={'task':'Analyze error','agent':'custom_api','error_output':'heartbeat ok\n'*100+'RuntimeError: database failed\n'}
    r=client.post('/v1/optimize',json=body)
    assert r.status_code==200
    result=r.json()['report']
    assert result['provider_tokens_saved'] is None
    assert result['execution_duration_ms'] is not None
    assert result['estimated_reduction_percent'] >= 0

def test_unavailable_provider_usage_never_inferred_from_estimates():
    r=optimize(OptimizeRequest(task='Hello'))
    assert r.report.provider_tokens_saved is None
    assert r.report.provider_usage is None
    assert r.report.estimated_reduction_percent is None

def test_cache_usage_not_double_counted():
    assert usage_counts({'prompt_tokens':100,'completion_tokens':20,'prompt_tokens_details':{'cached_tokens':40}})==(100,20,40)

def test_provider_usage_rejects_invalid_caches():
    with pytest.raises(ValueError):
        usage_counts({'prompt_tokens':10,'completion_tokens':10,'prompt_tokens_details':{'cached_tokens':11}})
