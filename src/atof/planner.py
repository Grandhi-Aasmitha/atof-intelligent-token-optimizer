"""Phase 3: policy-driven multi-feature selection with scoped conflicts.

The planner never authorizes file access or agent interception; all evidence is
provided explicitly by the caller. Feature overrides cannot bypass gates.
"""
import re
from .registry import FeatureRegistry
from .analyzer import Analysis
from .models import FeatureDecision, OptimizeRequest
from .adapter_policy import can_return_candidate
from .engines.base import PluginSpec

def _plan(request: OptimizeRequest, engines, analysis: Analysis, *, transport: str = "http_api") -> list[FeatureDecision]:
    decisions: list[FeatureDecision] = []
    selected: set[str] = set()
    available: list[PluginSpec] = []
    def relevance(spec):
        return int(bool(spec.task_pattern and re.search(spec.task_pattern, request.task, re.I)))

    for spec in engines.strategies(relevance=relevance):
        if request.feature_override and spec.feature_id != request.feature_override:
            continue
        if spec.evidence not in analysis.supplied_slots or (
                spec.evidence == 'files' and len(request.files) < spec.minimum_items):
            # Hints explain missing evidence; they never authorize or fabricate it.
            if (spec.evidence in analysis.requested_slots and
                    (spec.evidence not in analysis.supplied_slots)):
                decisions.append(FeatureDecision(feature_id=spec.feature_id, status='skipped',
                                  reason='structured_evidence_required'))
            continue
        if not can_return_candidate(request.agent, transport, request.delivery_mode):
            decisions.append(FeatureDecision(feature_id=spec.feature_id, status='unsupported',
                         reason='no_verified_context_delivery_path_for_agent'))
            continue
        if not engines.supports(spec.feature_id):
            decisions.append(FeatureDecision(feature_id=spec.feature_id, status='unsupported',
                         reason='no_registered_engine'))
            continue
        if not request.optimization_enabled:
            decisions.append(FeatureDecision(feature_id=spec.feature_id, status='skipped', reason='optimization_disabled'))
            continue
        if spec.applicable is not None:
            try:
                eligible = spec.applicable(request) is True
            except Exception:
                decisions.append(FeatureDecision(feature_id=spec.feature_id, status='failed',
                                                 reason='applicability_check_failed'))
                continue
            if not eligible:
                decisions.append(FeatureDecision(feature_id=spec.feature_id, status='skipped',
                                                 reason='plugin_not_applicable'))
                continue
        available.append(spec)

    if request.feature_override:
        if request.feature_override not in {s.feature_id for s in available}:
            if any(d.reason == 'optimization_disabled' for d in decisions):
                return decisions
            return [FeatureDecision(feature_id=request.feature_override,
                                    status='unsupported', reason='override_not_eligible')]
        available = [s for s in available if s.feature_id == request.feature_override]

    for spec in available:
        if any(f in selected for f in spec.conflicts) or any(
                spec.feature_id in engines.spec(f).conflicts for f in selected):
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
    return _plan(request, engines if engines is not None else EngineRegistry(), analysis, transport=transport)
