"""One stable interface for in-process and future licensed optimization engines."""
from dataclasses import dataclass
from .native_code import NativeCodeContextEngine
from .native_other import NativeRepositoryEngine, NativeDiffEngine, NativeTestLogEngine, NativeErrorEngine
from .base import OptimizationEngine

@dataclass(frozen=True)
class EngineDescriptor:
    feature_id: str
    implementation: str
    status: str

class EngineRegistry:
    def __init__(self, engines: list[OptimizationEngine] | None = None):
        active = engines if engines is not None else [
            NativeCodeContextEngine(), NativeRepositoryEngine(), NativeDiffEngine(),
            NativeTestLogEngine(), NativeErrorEngine(),
        ]
        self._engines = {}
        for engine in active:
            if engine.feature_id in self._engines:
                raise ValueError(f'duplicate optimization engine: {engine.feature_id}')
            self._engines[engine.feature_id] = engine

    def get(self, feature_id: str):
        return self._engines.get(feature_id)

    def capabilities(self):
        return [EngineDescriptor(feature_id=k, implementation=type(v).__name__, status='available')
                for k,v in sorted(self._engines.items())]

    def supports(self, feature_id: str) -> bool:
        return feature_id in self._engines
