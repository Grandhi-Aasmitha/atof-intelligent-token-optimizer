import uuid
from .analyzer import analyze
from .engines.native_code import NativeCodeContextEngine
from .models import OptimizationReport, OptimizeRequest, OptimizeResponse
from .planner import select
from .registry import FeatureRegistry
from .legacy.tokens import estimate_text

_registry=FeatureRegistry()
_engine=NativeCodeContextEngine()

def optimize(request:OptimizeRequest)->OptimizeResponse:
    analysis=analyze(request)
    decisions=select(request,analysis,_registry)
    report=OptimizationReport(request_id=str(uuid.uuid4()),intent=analysis.intent,agent=request.agent,original_estimated_tokens=estimate_text('\n'.join(f.content for f in request.files) or request.task),decisions=decisions)
    selected=next((d for d in decisions if d.feature_id=='coding.code_context' and d.status=='selected'),None)
    if selected is None or not request.execute:
        if selected and not request.execute:
            selected.status='applicable';selected.reason='dry_run_only'
        return OptimizeResponse(report=report)
    try:
        result=_engine.optimize(request)
        selected.estimated_before=result.before;selected.estimated_after=result.after
        report.original_estimated_tokens=result.before
        report.optimized_estimated_tokens=result.after
        report.estimated_reduction_tokens=max(0,result.before-result.after)
        report.warnings.extend(result.warnings)
        # This initial fidelity gate is intentionally conservative. Only a nonempty
        # reduced payload without unresolved dependencies is returned as optimized.
        unsafe = result.after >= result.before or not result.content.strip() or any(w.startswith('unresolved_dependencies:') for w in result.warnings)
        if unsafe:
            selected.status='skipped';selected.reason='not_smaller_or_unresolved_dependencies'
            report.optimized_estimated_tokens=None;report.estimated_reduction_tokens=None
            return OptimizeResponse(report=report)
        selected.status='executed';selected.reason='optimized_payload_returned_to_api_caller'
        report.delivery_status='payload_returned_to_client'
        report.warnings.append('API payload returned; model consumption and provider token savings are not verified')
        return OptimizeResponse(optimized_context=result.content,report=report)
    except (ValueError,RuntimeError,SyntaxError) as exc:
        selected.status='failed';selected.reason=type(exc).__name__
        report.warnings.append('Optimizer failed safely; original context was not altered')
        return OptimizeResponse(report=report)
