from .registry import FeatureRegistry
from .analyzer import Analysis
from .models import FeatureDecision, OptimizeRequest

# Phase 1: conservative deterministic rules; no inferred authorization.
# Other catalog items are discoverable but not executed until separately implemented.
def select(request:OptimizeRequest, analysis:Analysis, registry:FeatureRegistry)->list[FeatureDecision]:
    decisions=[]
    if 'source' in analysis.evidence_types:
        supported=request.delivery_mode=='return_payload' and request.agent=='custom_api'
        if not supported:
            decisions.append(FeatureDecision(feature_id='coding.code_context',status='unsupported',reason='no_verified_context_delivery_path_for_agent'))
        else:
            decisions.append(FeatureDecision(feature_id='coding.code_context',status='selected',reason='authorized_source_evidence_supplied'))
        # repository retrieval becomes applicable to multi-file requests, but isn't implemented in Phase 1
        if len(request.files)>1:
            decisions.append(FeatureDecision(feature_id='coding.repository_retrieval',status='unsupported',reason='strategy_not_integrated_in_phase1'))
    # Non-implemented features show only when positively relevant; do not show entire registry.
    if 'diff' in analysis.evidence_types:
        decisions.append(FeatureDecision(feature_id='coding.code_diff',status='unsupported',reason='strategy_not_integrated_in_phase1'))
    if 'test' in analysis.evidence_types:
        decisions.append(FeatureDecision(feature_id='coding.test_log',status='unsupported',reason='strategy_not_integrated_in_phase1'))
    if 'error' in analysis.evidence_types:
        decisions.append(FeatureDecision(feature_id='coding.error_context',status='unsupported',reason='strategy_not_integrated_in_phase1'))
    return decisions
