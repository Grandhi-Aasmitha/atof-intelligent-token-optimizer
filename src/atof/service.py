"""Phase 2 engine dispatch; no model-consumption or provider-savings claims."""
import uuid
from .analyzer import analyze
from .engines.registry import EngineRegistry
from .models import OptimizationReport, OptimizeRequest, OptimizeResponse
from .planner import select
from .registry import FeatureRegistry
from .legacy.tokens import estimate_text

_registry = FeatureRegistry()
_engines = EngineRegistry()

def optimize(request: OptimizeRequest) -> OptimizeResponse:
    analysis = analyze(request)
    decisions = select(request, analysis, _registry, _engines)
    # Baseline is evidence-specific; engine adapters replace it with their
    # equivalent before count after a successful execution.
    all_evidence = '\n'.join([*(f.content for f in request.files), request.diff,
                              request.test_output, request.error_output])
    report = OptimizationReport(
        request_id=str(uuid.uuid4()), intent=analysis.intent, agent=request.agent,
        original_estimated_tokens=estimate_text(all_evidence.strip() or request.task),
        decisions=decisions,
    )
    selected = next((d for d in decisions if d.status == 'selected'), None)
    if selected is None or not request.execute:
        if selected and not request.execute:
            selected.status = 'applicable'
            selected.reason = 'dry_run_only'
        return OptimizeResponse(report=report)

    engine = _engines.get(selected.feature_id)
    if engine is None:
        selected.status = 'unsupported'
        selected.reason = 'no_registered_engine'
        return OptimizeResponse(report=report)

    report.engine = type(engine).__name__
    try:
        result = engine.optimize(request)
        selected.estimated_before = result.before
        selected.estimated_after = result.after
        report.original_estimated_tokens = result.before
        report.warnings.extend(result.warnings)
        # All results are advisory excerpts, never edits to original sources.
        unsafe = (result.after >= result.before or not result.content.strip() or
                  any(w.startswith('unresolved_dependencies:') for w in result.warnings))
        if unsafe:
            selected.status = 'skipped'
            selected.reason = 'not_smaller_or_unresolved_dependencies'
            return OptimizeResponse(report=report)
        selected.status = 'executed'
        selected.reason = 'optimized_payload_returned_to_api_caller'
        report.executed_feature = selected.feature_id
        report.optimized_estimated_tokens = result.after
        report.estimated_reduction_tokens = result.before - result.after
        report.delivery_status = 'payload_returned_to_client'
        report.warnings.append('Payload returned to caller only; model consumption and provider savings unverified')
        return OptimizeResponse(optimized_context=result.content, report=report)
    except (ValueError, RuntimeError, SyntaxError) as exc:
        selected.status = 'failed'
        selected.reason = type(exc).__name__
        report.warnings.append('Optimizer failed safely; original evidence was not altered')
        return OptimizeResponse(report=report)
