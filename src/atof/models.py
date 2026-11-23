from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field, model_validator

class EvidenceFile(BaseModel):
    path: str = Field(min_length=1, max_length=1024)
    content: str = Field(max_length=300_000)

class OptimizeRequest(BaseModel):
    task: str = Field(min_length=1, max_length=20_000)
    files: list[EvidenceFile] = Field(default_factory=list, max_length=100)
    diff: str = Field(default="", max_length=300_000)
    test_output: str = Field(default="", max_length=500_000)
    error_output: str = Field(default="", max_length=500_000)
    feature_override: str | None = None
    max_optimizers: int = Field(default=4, ge=1, le=5)
    agent: Literal["custom_api", "codex", "copilot", "claude"] = "custom_api"
    token_budget: int = Field(default=1600, ge=64, le=200_000)
    execute: bool = True
    delivery_mode: Literal["return_payload", "observe_only"] = "return_payload"

    @model_validator(mode="after")
    def unique_files(self):
        paths = [f.path for f in self.files]
        if len(paths) != len(set(paths)):
            raise ValueError("duplicate evidence paths")
        return self

class FeatureDecision(BaseModel):
    feature_id: str
    status: Literal["applicable", "selected", "executed", "candidate_only", "skipped", "unsupported", "failed"]
    reason: str
    estimated_before: int | None = None
    estimated_after: int | None = None

class OptimizationReport(BaseModel):
    schema_version: str = "atof-report/1"
    request_id: str
    intent: str
    agent: str
    original_estimated_tokens: int
    optimized_estimated_tokens: int | None = None
    estimated_reduction_tokens: int | None = None
    provider_tokens_saved: int | None = None
    delivery_status: Literal["not_attempted", "payload_returned_to_client", "observed_only"] = "not_attempted"
    decisions: list[FeatureDecision] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    engine: str | None = None
    executed_feature: str | None = None
    executed_features: list[str] = Field(default_factory=list)
    stage_results: list[dict[str, str | int | None]] = Field(default_factory=list)
    original_context_estimated_tokens: int | None = None
    estimated_reduction_percent: float | None = None
    measurement_method: str = "local_heuristic_estimate"
    provider_usage: dict | None = None
    fidelity_status: Literal["not_evaluated", "passed", "rejected"] = "not_evaluated"
    fidelity_checks: list[dict[str, str | int | bool]] = Field(default_factory=list)
    execution_duration_ms: float | None = None

class OptimizeResponse(BaseModel):
    optimized_context: str | None = None
    report: OptimizationReport
