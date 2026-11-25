from dataclasses import dataclass
from typing import Protocol, Callable
from ..models import OptimizeRequest

@dataclass(frozen=True)
class EngineResult:
    content: str
    before: int
    after: int
    warnings: tuple[str,...] = ()

@dataclass(frozen=True)
class PluginSpec:
    feature_id: str
    evidence: str
    priority: int
    conflicts: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    validator: Callable[[str, str], bool] | None = None
    minimum_items: int = 1

class OptimizationEngine(Protocol):
    feature_id: str
    def optimize(self, request: OptimizeRequest) -> EngineResult: ...
