"""Phase 3: analyze, plan, execute compatible optimizers, report honestly."""
import uuid
from .analyzer import analyze
from .engines.registry import EngineRegistry
from .models import OptimizationReport, OptimizeRequest, OptimizeResponse
from .planner import select
from .registry import FeatureRegistry
from .legacy.tokens import estimate_text
from .orchestrator import run_pipeline, source_sections, compose

_registry = FeatureRegistry()
_engines = EngineRegistry()

def optimize(request: OptimizeRequest, *, transport: str = "http_api", record_metrics: bool = True, source_kind: str | None = None) -> OptimizeResponse:
    if transport not in ("http_api", "mcp_explicit", "owned_adapter"):
        raise ValueError("unsupported internal execution transport")
    from .control import effective_request
    provenance = source_kind or ('agent_tool' if transport == 'mcp_explicit' else 'local_api')
    request, policy = effective_request(request, diagnostic=provenance in ('developer_test', 'synthetic_test', 'controlled_validation'))
    analysis = analyze(request)
    decisions = select(request, analysis, _registry, _engines, transport=transport)
    sections = source_sections(request)
    original = compose(sections)
    report = OptimizationReport(request_id=str(uuid.uuid4()), intent=analysis.intent,
                                agent=request.agent,
                                original_estimated_tokens=estimate_text(original or request.task),
                                decisions=decisions, execution_transport=transport,
                                source_kind=provenance, control_policy=policy)
    if policy in ('disabled', 'settings_unavailable'):
        report.warnings.append('ATOF optimization is disabled by local control settings; retain original evidence.')
    report.context_breakdown = {key: estimate_text(value) for key, value in sections.items()}
    report.token_budget = request.token_budget
    response = run_pipeline(request, decisions, report, _engines)
    effective = report.optimized_estimated_tokens if response.optimized_context is not None else report.original_estimated_tokens
    report.budget_status = 'within_budget' if effective <= request.token_budget else 'over_budget'
    if report.budget_status == 'over_budget':
        report.warnings.append('Evidence exceeds estimated budget; no unsafe truncation or provider limit guarantee')
    if transport == "mcp_explicit" and response.optimized_context is not None:
        response.report.delivery_status = "mcp_tool_result_returned"
    try:
        from .analytics import record
        if record_metrics:
            record(response)
    except (OSError, ValueError, RuntimeError, __import__('sqlite3').Error):
        pass
    return response
