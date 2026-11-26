"""One stable interface for in-process and future licensed optimization engines."""
from dataclasses import dataclass
import re
from .native_code import NativeCodeContextEngine
from .native_other import NativeRepositoryEngine, NativeDiffEngine, NativeTestLogEngine, NativeErrorEngine
from .base import OptimizationEngine, PluginSpec
from .generic import GenericContextEngine, GenericToolOutputEngine

# Legacy plugins retain their original interface; new plugins declare spec.
LEGACY_SPECS = {
    'coding.error_context': PluginSpec('coding.error_context', 'error_output', 100, task_pattern=r'\b(error|exception|traceback|root cause|stack trace|debug)\b'),
    'coding.test_log': PluginSpec('coding.test_log', 'test_output', 90, task_pattern=r'\b(tests?|pytest|junit|assertion|test failures?)\b'),
    'coding.code_diff': PluginSpec('coding.code_diff', 'diff', 80, task_pattern=r'\b(diff|patch|changes|pull request)\b'),
    'coding.code_context': PluginSpec('coding.code_context', 'files', 70, ('coding.repository_retrieval',), task_pattern=r'\b(function|method|symbol|class|dependencies)\b'),
    'coding.repository_retrieval': PluginSpec('coding.repository_retrieval', 'files', 60, ('coding.code_context',), minimum_items=2, task_pattern=r'\b(repository|repo|codebase|locate|find)\b'),
}

@dataclass(frozen=True)
class EngineDescriptor:
    feature_id: str
    implementation: str
    status: str
    evidence: str
    priority: int

class EngineRegistry:
    def __init__(self, engines: list[OptimizationEngine] | None = None):
        active = engines if engines is not None else [
            NativeCodeContextEngine(), NativeRepositoryEngine(), NativeDiffEngine(),
            NativeTestLogEngine(), NativeErrorEngine(), GenericContextEngine(), GenericToolOutputEngine(),
        ]
        self._engines = {}
        self._specs = {}
        for engine in active:
            if engine.feature_id in self._engines:
                raise ValueError(f'duplicate optimization engine: {engine.feature_id}')
            spec = getattr(engine, 'spec', LEGACY_SPECS.get(engine.feature_id))
            if not isinstance(spec, PluginSpec) or spec.feature_id != engine.feature_id or spec.evidence not in ('files','diff','test_output','error_output','context','tool_output'):
                raise ValueError(f'invalid plugin metadata: {engine.feature_id}')
            if spec.minimum_items < 1 or (spec.evidence != 'files' and spec.minimum_items != 1):
                raise ValueError(f'invalid plugin evidence cardinality: {engine.feature_id}')
            if engine.feature_id not in LEGACY_SPECS and not callable(spec.validator):
                raise ValueError(f'plugin requires a fidelity validator: {engine.feature_id}')
            if spec.task_pattern is not None:
                re.compile(spec.task_pattern, re.I)
            if spec.applicable is not None and not callable(spec.applicable):
                raise ValueError(f'invalid applicability predicate: {engine.feature_id}')
            self._engines[engine.feature_id] = engine
            self._specs[engine.feature_id] = spec
        # Validate the registered dependency graph before accepting requests.
        self.strategies()

    def strategies(self, *, relevance=None):
        # Stable priority among ready plugins; a dependency always precedes its dependent.
        pending = dict(self._specs)
        ordered = []
        while pending:
            ready = [s for s in pending.values() if not set(s.depends_on).intersection(pending)]
            if not ready:
                raise ValueError('cyclic optimizer dependencies')
            spec = min(ready, key=lambda s: (-(relevance(s) if relevance else 0), -s.priority, s.feature_id))
            ordered.append(spec)
            del pending[spec.feature_id]
        return ordered

    def spec(self, feature_id):
        return self._specs[feature_id]

    def get(self, feature_id: str):
        return self._engines.get(feature_id)

    def capabilities(self):
        return [EngineDescriptor(feature_id=k, implementation=type(v).__name__, status='available',
                                 evidence=self._specs[k].evidence, priority=self._specs[k].priority)
                for k,v in sorted(self._engines.items())]

    def supports(self, feature_id: str) -> bool:
        return feature_id in self._engines
