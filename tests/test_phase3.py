"""Phase 3: selection, composition, conflicts, gate, fallback and API."""
from fastapi.testclient import TestClient
from atof.api import app
from atof.engines.base import EngineResult
from atof.engines.registry import EngineRegistry
from atof.models import OptimizeRequest
from atof.orchestrator import run_pipeline, source_sections, compose
from atof.planner import select
from atof.analyzer import analyze
from atof.registry import FeatureRegistry
from atof.service import optimize
from atof.models import OptimizationReport

client=TestClient(app)

def req(**fields):
    body={'task':'Fix a failing test and explain the code','agent':'custom_api'}
    body.update(fields)
    return OptimizeRequest(**body)

NOISE='heartbeat ok\n'*130
TEST_NOISE='test_ok PASSED\n'*130
DIFF=('diff --git a/file.py b/file.py\n--- a/file.py\n+++ b/file.py\n@@ -1,5 +1,5 @@\n'+
      ' context\n'*100+'-old line\n+new line\n'+' context\n'*100)

def test_selection_three_independent_evidence_types():
    response=optimize(req(diff=DIFF, test_output=TEST_NOISE+'test_bad FAILED\nE AssertionError\n',error_output=NOISE+'RuntimeError: bad\n'))
    assert {'coding.error_context','coding.test_log','coding.code_diff'}.issubset(
        {d.feature_id for d in response.report.decisions if d.status in ('executed','skipped')})
    assert len(response.report.executed_features)>=2
    assert '-old line' in response.optimized_context and '+new line' in response.optimized_context
    assert 'RuntimeError: bad' in response.optimized_context
    assert 'test_bad FAILED' in response.optimized_context
    assert response.report.estimated_reduction_tokens>0
    assert response.report.provider_tokens_saved is None

def test_conflicting_source_strategies_do_not_both_run():
    files=[{'path':'target.py','content':'def target(): return 1\n'+'# blah\n'*120},
           {'path':'other.py','content':'def unrelated(): return 2\n'+'# filler\n'*120}]
    result=optimize(req(files=files))
    names={d.feature_id:d for d in result.report.decisions}
    assert names['coding.repository_retrieval'].reason=='conflicts_with_selected_strategy'
    assert len([f for f in result.report.executed_features if f in names])<=1

def test_budget_caps_number_of_optimizers():
    result=optimize(req(diff=DIFF,test_output=TEST_NOISE,error_output=NOISE+'RuntimeError: fail',max_optimizers=1,execute=False))
    assert len([d for d in result.report.decisions if d.reason=='optimizer_execution_limit'])==2
    assert result.optimized_context is None

def test_override_runs_only_requested_eligible_feature():
    result=optimize(req(diff=DIFF,test_output=TEST_NOISE,feature_override='coding.code_diff'))
    assert [d.feature_id for d in result.report.decisions]==['coding.code_diff']
    assert result.report.executed_features==['coding.code_diff']

def test_unsupported_override_never_bypasses_capabilities():
    result=optimize(req(agent='copilot',diff=DIFF,feature_override='coding.code_diff'))
    assert result.optimized_context is None
    assert any(d.reason=='override_not_eligible' for d in result.report.decisions)

def test_failures_preserve_original_sections(monkeypatch):
    from atof import service
    class Bad:
        feature_id='coding.error_context'
        def optimize(self, request):
            raise RuntimeError('sensitive error string')
    good=service._engines
    reg=EngineRegistry([Bad(), *[eng for eng in good._engines.values() if eng.feature_id!='coding.error_context']])
    monkeypatch.setattr(service,'_engines',reg)
    result=optimize(req(error_output=NOISE+'RuntimeError: SECRET',test_output=TEST_NOISE+'test_bad FAILED'))
    assert 'RuntimeError: SECRET' in result.optimized_context
    assert 'sensitive error string' not in str(result.report.model_dump())
    assert any(d.status=='failed' for d in result.report.decisions)
    assert result.report.executed_features

def test_untouched_evidence_retained_when_other_stage_executes():
    sample='single failure, no reducible payload'
    result=optimize(req(test_output=TEST_NOISE+'test_bad FAILED',error_output=sample))
    assert result.optimized_context
    assert sample in result.optimized_context

def test_no_reducing_stages_returns_none():
    result=optimize(req(error_output='RuntimeError: x'))
    assert result.optimized_context is None
    assert result.report.estimated_reduction_tokens is None

def test_stages_do_not_modify_inputs():
    request=req(test_output=TEST_NOISE,error_output=NOISE+'RuntimeError: ok')
    before=request.model_dump()
    optimize(request)
    assert request.model_dump()==before

def test_analyze_is_dry_run_for_all_features():
    response=client.post('/v1/analyze',json=req(diff=DIFF,test_output=TEST_NOISE,error_output=NOISE).model_dump())
    assert response.status_code==200
    data=response.json()
    assert data['optimized_context'] is None
    assert data['report']['executed_features']==[]
    assert all(d['status'] != 'executed' for d in data['report']['decisions'])

def test_api_rejects_invalid_max_optimizers():
    assert client.post('/v1/optimize',json=req(max_optimizers=1).model_dump() | {'max_optimizers':0}).status_code==422

def test_response_has_consistent_composite_counts():
    result=optimize(req(diff=DIFF,test_output=TEST_NOISE+'test_bad FAILED'))
    from atof.legacy.tokens import estimate_text
    if result.optimized_context:
        assert result.report.optimized_estimated_tokens==estimate_text(result.optimized_context)
        assert result.report.estimated_reduction_tokens==result.report.original_estimated_tokens-result.report.optimized_estimated_tokens

def test_noncustom_agent_never_optimizes_multiple():
    result=optimize(req(agent='codex',diff=DIFF,test_output=TEST_NOISE,error_output=NOISE))
    assert result.optimized_context is None
    assert all(d.status=='unsupported' for d in result.report.decisions)
