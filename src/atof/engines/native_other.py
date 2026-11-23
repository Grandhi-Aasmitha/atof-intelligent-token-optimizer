"""Small, explicit adapters for previously reviewed ATOF native algorithms."""
from ..legacy.coding import repository_retrieval, code_diff, test_log, error_context
from ..models import OptimizeRequest
from .base import EngineResult

class NativeRepositoryEngine:
    feature_id = 'coding.repository_retrieval'
    def optimize(self, request: OptimizeRequest) -> EngineResult:
        data = repository_retrieval(request.task, [f.model_dump() for f in request.files], request.token_budget)
        content = '\n\n'.join(f"# {f['path']}\n{f['content']}" for f in data['selected_files'])
        return EngineResult(content, data['estimated_full_tokens'], data['estimated_selected_tokens'], tuple(data['warnings']))

class NativeDiffEngine:
    feature_id = 'coding.code_diff'
    def optimize(self, request: OptimizeRequest) -> EngineResult:
        data = code_diff(request.diff, token_budget=request.token_budget)
        if not data['changes_preserved']:
            raise ValueError('diff_change_line_preservation_failed')
        return EngineResult(data['context'], data['estimated_full_tokens'], data['estimated_optimized_tokens'], tuple(data['warnings']))

class NativeTestLogEngine:
    feature_id = 'coding.test_log'
    def optimize(self, request: OptimizeRequest) -> EngineResult:
        data = test_log(request.test_output, token_budget=request.token_budget)
        return EngineResult(data['context'], data['estimated_full_tokens'], data['estimated_optimized_tokens'], tuple(data['warnings']))

class NativeErrorEngine:
    feature_id = 'coding.error_context'
    def optimize(self, request: OptimizeRequest) -> EngineResult:
        data = error_context(request.error_output, token_budget=request.token_budget, files=[f.model_dump() for f in request.files])
        return EngineResult(data['context'], data['estimated_full_tokens'], data['estimated_optimized_tokens'], tuple(data['warnings']))
