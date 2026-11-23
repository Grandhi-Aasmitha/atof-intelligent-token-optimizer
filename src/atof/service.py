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

def optimize(request: OptimizeRequest, *, transport: str = "http_api") -> OptimizeResponse:
    if transport not in ("http_api", "mcp_explicit"):
        raise ValueError("unsupported internal execution transport")
    analysis = analyze(request)
    decisions = select(request, analysis, _registry, _engines, transport=transport)
    original = compose(source_sections(request))
    report = OptimizationReport(request_id=str(uuid.uuid4()), intent=analysis.intent,
                                agent=request.agent,
                                original_estimated_tokens=estimate_text(original or request.task),
                                decisions=decisions, execution_transport=transport)
    response = run_pipeline(request, decisions, report, _engines)
    if transport == "mcp_explicit" and response.optimized_context is not None:
        response.report.delivery_status = "mcp_tool_result_returned"
    try:
        from .analytics import record
        record(response)
    except (OSError, ValueError, RuntimeError, __import__('sqlite3').Error):
        pass
    return response
