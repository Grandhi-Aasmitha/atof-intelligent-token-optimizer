"""One stable interface for in-process and future licensed optimization engines."""
from dataclasses import dataclass
from .native_code import NativeCodeContextEngine
from .native_other import NativeRepositoryEngine, NativeDiffEngine, NativeTestLogEngine, NativeErrorEngine
from .base import OptimizationEngine, PluginSpec
from .generic import GenericContextEngine, GenericToolOutputEngine

# Legacy plugins retain their original interface; new plugins declare spec.
LEGACY_SPECS = {
    'coding.error_context': PluginSpec('coding.error_context', 'error_output', 100),
    'coding.test_log': PluginSpec('coding.test_log', 'test_output', 90),
    'coding.code_diff': PluginSpec('coding.code_diff', 'diff', 80),
    'coding.code_context': PluginSpec('coding.code_context', 'files', 70, ('coding.repository_retrieval',)),
    'coding.repository_retrieval': PluginSpec('coding.repository_retrieval', 'files', 60, ('coding.code_context',)),
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
            if engine.feature_id not in LEGACY_SPECS and not callable(spec.validator):
                raise ValueError(f'plugin requires a fidelity validator: {engine.feature_id}')
            self._engines[engine.feature_id] = engine
            self._specs[engine.feature_id] = spec

    def strategies(self):
        return sorted(self._specs.values(), key=lambda s: (-s.priority, s.feature_id))

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
