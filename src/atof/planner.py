"""Phase 2 deterministic, delivery-aware feature selection."""
from .registry import FeatureRegistry
from .analyzer import Analysis
from .models import FeatureDecision, OptimizeRequest

FEATURE_EVIDENCE = (
    ('coding.error_context', 'error', 'error_output'),
    ('coding.test_log', 'test', 'test_output'),
    ('coding.code_diff', 'diff', 'diff'),
    ('coding.code_context', 'source', 'files'),
    ('coding.repository_retrieval', 'source', 'files'),
)

def select(request: OptimizeRequest, analysis: Analysis, registry: FeatureRegistry, engines=None) -> list[FeatureDecision]:
    from .engines.registry import EngineRegistry
    engines = engines or EngineRegistry()
    decisions = []
    candidates = []
    for feature_id, evidence_type, field in FEATURE_EVIDENCE:
        if evidence_type not in analysis.evidence_types:
            continue
        if feature_id == 'coding.repository_retrieval' and len(request.files) < 2:
            continue
        # Do not use regex matches in task text as evidence for a transformation.
        if not getattr(request, field):
            decisions.append(FeatureDecision(feature_id=feature_id, status='skipped', reason='structured_evidence_required'))
            continue
        if request.agent != 'custom_api' or request.delivery_mode != 'return_payload':
            decisions.append(FeatureDecision(feature_id=feature_id, status='unsupported', reason='no_verified_context_delivery_path_for_agent'))
            continue
        if not engines.supports(feature_id):
            decisions.append(FeatureDecision(feature_id=feature_id, status='unsupported', reason='no_registered_engine'))
            continue
        candidates.append(feature_id)

    chosen = request.feature_override if request.feature_override else (candidates[0] if candidates else None)
    if request.feature_override and chosen not in candidates:
        # Never let caller overrides circumvent evidence and adapter capability gates.
        decisions.append(FeatureDecision(feature_id=chosen, status='unsupported', reason='override_not_eligible'))
        chosen = None
    for feature_id in candidates:
        if feature_id == chosen:
            decisions.append(FeatureDecision(feature_id=feature_id, status='selected', reason='supported_authorized_structured_evidence'))
        else:
            decisions.append(FeatureDecision(feature_id=feature_id, status='applicable', reason='deferred_single_engine_execution'))
    return decisions
