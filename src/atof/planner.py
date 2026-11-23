"""Phase 3: policy-driven multi-feature selection with scoped conflicts.

The planner never authorizes file access or agent interception; all evidence is
provided explicitly by the caller. Feature overrides cannot bypass gates.
"""
from dataclasses import dataclass
from .registry import FeatureRegistry
from .analyzer import Analysis
from .models import FeatureDecision, OptimizeRequest

@dataclass(frozen=True)
class Strategy:
    feature_id: str
    evidence: str
    priority: int
    conflicts: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()

STRATEGIES = (
    Strategy('coding.error_context', 'error_output', 100),
    Strategy('coding.test_log', 'test_output', 90),
    Strategy('coding.code_diff', 'diff', 80),
    Strategy('coding.code_context', 'files', 70, ('coding.repository_retrieval',)),
    Strategy('coding.repository_retrieval', 'files', 60, ('coding.code_context',)),
)

def _plan(request: OptimizeRequest, engines, request_analysis_evidence: frozenset[str], *, transport: str = "http_api") -> list[FeatureDecision]:
    decisions: list[FeatureDecision] = []
    selected: set[str] = set()
    available: list[Strategy] = []
    for spec in STRATEGIES:
        if spec.evidence == 'files' and not request.files:
            continue
        if spec.evidence != 'files' and not getattr(request, spec.evidence).strip():
            # Classifier may infer evidence from a prompt, but without its
            # actual structured payload it cannot be transformed.
            kind = {'diff':'diff', 'test_output':'test', 'error_output':'error'}[spec.evidence]
            if kind in request_analysis_evidence:
                decisions.append(FeatureDecision(feature_id=spec.feature_id, status='skipped',
                                  reason='structured_evidence_required'))
            continue
        if spec.feature_id == 'coding.repository_retrieval' and len(request.files) < 2:
            continue
        if request.delivery_mode != 'return_payload' or not (request.agent == 'custom_api' or (transport == 'mcp_explicit' and request.agent in ('codex', 'copilot', 'claude'))):
            decisions.append(FeatureDecision(feature_id=spec.feature_id, status='unsupported',
                         reason='no_verified_context_delivery_path_for_agent'))
            continue
        if not engines.supports(spec.feature_id):
            decisions.append(FeatureDecision(feature_id=spec.feature_id, status='unsupported',
                         reason='no_registered_engine'))
            continue
        available.append(spec)

    if request.feature_override:
        if request.feature_override not in {s.feature_id for s in available}:
            decisions.append(FeatureDecision(feature_id=request.feature_override,
                                            status='unsupported', reason='override_not_eligible'))
            return decisions
        available = [s for s in available if s.feature_id == request.feature_override]

    for spec in available:
        if any(f in selected for f in spec.conflicts):
            decisions.append(FeatureDecision(feature_id=spec.feature_id, status='skipped',
                                            reason='conflicts_with_selected_strategy'))
        elif not set(spec.depends_on).issubset(selected):
            decisions.append(FeatureDecision(feature_id=spec.feature_id, status='skipped',
                                            reason='missing_strategy_dependency'))
        elif len(selected) >= request.max_optimizers:
            decisions.append(FeatureDecision(feature_id=spec.feature_id, status='applicable',
                                            reason='optimizer_execution_limit'))
        else:
            selected.add(spec.feature_id)
            decisions.append(FeatureDecision(feature_id=spec.feature_id, status='selected',
                                            reason='authorized_evidence_and_capability_verified'))
    return decisions

def select(request: OptimizeRequest, analysis: Analysis, registry: FeatureRegistry, engines=None, *, transport: str = "http_api") -> list[FeatureDecision]:
    from .engines.registry import EngineRegistry
    return _plan(request, engines if engines is not None else EngineRegistry(), analysis.evidence_types, transport=transport)
