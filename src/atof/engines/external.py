"""Boundary for future *authorized* external optimization engines.

No third-party code is vendored, downloaded, executed or imported. External
implementations need their own license review and tested transport contract.
"""
from ..models import OptimizeRequest
from .base import EngineResult

class ExternalEngineUnavailable(RuntimeError):
    pass

class ExternalEngineAdapter:
    def __init__(self, feature_id: str):
        self.feature_id = feature_id

    def optimize(self, request: OptimizeRequest) -> EngineResult:
        raise ExternalEngineUnavailable('external_engine_not_configured_or_licensed')
