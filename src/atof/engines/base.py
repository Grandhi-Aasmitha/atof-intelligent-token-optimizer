from dataclasses import dataclass
from typing import Protocol
from ..models import OptimizeRequest

@dataclass(frozen=True)
class EngineResult:
    content: str
    before: int
    after: int
    warnings: tuple[str,...] = ()

class OptimizationEngine(Protocol):
    feature_id: str
    def optimize(self, request: OptimizeRequest) -> EngineResult: ...
