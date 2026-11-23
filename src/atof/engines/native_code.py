from ..legacy.coding import code_context
from ..models import OptimizeRequest
from .base import EngineResult

class NativeCodeContextEngine:
    feature_id='coding.code_context'
    def optimize(self, request: OptimizeRequest)->EngineResult:
        result=code_context(task=request.task,files=[f.model_dump() for f in request.files],token_budget=request.token_budget)
        return EngineResult(content=result['context'],before=result['estimated_full_tokens'],after=result['estimated_optimized_tokens'],warnings=tuple(result['warnings'] + (['unresolved_dependencies: '+', '.join(result['unresolved_dependencies'])] if result['unresolved_dependencies'] else [])))
