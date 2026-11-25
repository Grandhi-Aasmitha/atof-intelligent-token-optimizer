"""User-facing projection of the internal execution trace.

Only a feature that contributed to the accepted candidate is an applied
feature. The internal trace remains available for explicit diagnostics/tests.
"""
from .models import OptimizeResponse


def applied_response(response: OptimizeResponse) -> OptimizeResponse:
    report = response.report
    accepted = bool(response.optimized_context and report.estimated_reduction_tokens
                    and report.estimated_reduction_tokens > 0)
    ids = set(report.executed_features) if accepted else set()
    decisions = [d for d in report.decisions if d.status == 'executed' and d.feature_id in ids]
    ids = {d.feature_id for d in decisions}
    hidden = {d.feature_id for d in report.decisions if d.feature_id not in ids}
    warnings = [w for w in report.warnings if not any(name in w for name in hidden)]
    if any(d.status == 'failed' or d.reason.startswith('fidelity_') for d in report.decisions):
        warnings.append('Some candidate transformations failed or were rejected; original evidence retained.')
    applied = [name for name in report.executed_features if name in ids]
    projected = report.model_copy(update={
        'decisions': decisions,
        'executed_features': applied,
        'executed_feature': applied[0] if applied else None,
        'engine': report.engine if applied else None,
        'stage_results': [s for s in report.stage_results
                          if s.get('feature_id') in ids and s.get('status') == 'executed'],
        'fidelity_checks': [s for s in report.fidelity_checks if s.get('feature_id') in ids],
        'warnings': list(dict.fromkeys(warnings)),
    })
    return response.model_copy(update={'report': projected})
