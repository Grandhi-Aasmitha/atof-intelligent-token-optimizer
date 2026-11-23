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

def optimize(request: OptimizeRequest) -> OptimizeResponse:
    analysis = analyze(request)
    decisions = select(request, analysis, _registry, _engines)
    original = compose(source_sections(request))
    report = OptimizationReport(request_id=str(uuid.uuid4()), intent=analysis.intent,
                                agent=request.agent,
                                original_estimated_tokens=estimate_text(original or request.task),
                                decisions=decisions)
    return run_pipeline(request, decisions, report, _engines)
