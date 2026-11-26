"""Transport-neutral adapter SDK. No implicit provider call or native interception."""
from dataclasses import dataclass
from typing import Any, Callable
from .adapter_policy import get_adapter, MCP_AGENTS
from .models import OptimizeRequest, OptimizeResponse
from .service import optimize
from .reporting import applied_response
from .orchestrator import compose, source_sections
from .legacy.tokens import estimate_text
from .premodel import assemble
from .analytics import record
import sqlite3


class UnsupportedAdapter(ValueError):
    pass


@dataclass(frozen=True)
class PreparedInput:
    adapter_id: str
    prompt: str
    original_prompt_estimate: int
    prepared_prompt_estimate: int
    response: OptimizeResponse

    def public(self):
        return {"adapter_id": self.adapter_id, "prompt": self.prompt,
                "original_prompt_estimate": self.original_prompt_estimate,
                "prepared_prompt_estimate": self.prepared_prompt_estimate,
                "prompt_estimated_reduction": self.original_prompt_estimate-self.prepared_prompt_estimate,
                "report": self.response.report.model_dump(mode="json"),
                "model_consumption_verified": False, "provider_savings_verified": False}


def _record(response):
    try:
        record(response)
    except (OSError, ValueError, RuntimeError, sqlite3.Error):
        pass


def _clear(response, status, warning):
    return OptimizeResponse(report=response.report.model_copy(update={
        "delivery_status":status, "optimized_estimated_tokens":None,
        "estimated_reduction_tokens":None, "estimated_reduction_percent":None,
        "executed_features":[], "executed_feature":None, "engine":None, "decisions":[],
        "stage_results":[], "fidelity_checks":[], "warnings":[warning],
    }))


class AgentAdapter:
    def __init__(self, adapter_id: str):
        try:
            self.spec = get_adapter(adapter_id)
        except KeyError:
            raise UnsupportedAdapter("Unknown adapter") from None

    def tool(self, request: OptimizeRequest, *, synthetic=False):
        """Only the configured in-process MCP server calls this method."""
        if self.spec.transport != "mcp_explicit" or self.spec.agent not in MCP_AGENTS:
            raise UnsupportedAdapter("Not an explicit MCP adapter")
        bound = request.model_copy(update={"agent":self.spec.agent, "delivery_mode":"return_payload"})
        result = optimize(bound, transport="mcp_explicit",
                          source_kind="synthetic_test" if synthetic else "agent_tool")
        return applied_response(result) if bound.execute else result

    def prepare(self, request: OptimizeRequest, *, persist=True):
        """Owned single-turn structured input; caller must supply authorized evidence."""
        if self.spec.transport != "owned_adapter":
            raise UnsupportedAdapter("This adapter does not own downstream input")
        if not request.execute or request.delivery_mode != "return_payload":
            raise ValueError("Preparation requires execute and return_payload")
        if request.agent not in ("custom_api", self.spec.agent):
            raise ValueError("Request agent conflicts with adapter")
        bound = request.model_copy(update={"agent": self.spec.agent})
        evidence = compose(source_sections(bound))
        original = assemble(bound.task, evidence)
        response = applied_response(optimize(bound, transport="owned_adapter",
                                            record_metrics=False, source_kind="owned_adapter"))
        candidate = response.optimized_context
        prepared = assemble(bound.task, candidate) if candidate else original
        before, after = estimate_text(original), estimate_text(prepared)
        if not candidate or response.report.fidelity_status != "passed" or after >= before:
            response = _clear(response, "owned_payload_prepared",
                              "No accepted reduction; original task and evidence retained.")
            prepared, after = original, before
        else:
            response.report.delivery_status = "owned_payload_prepared"
        if persist:
            _record(response)
        return PreparedInput(self.spec.id, prepared, before, after, response)

    def dispatch(self, request: OptimizeRequest, sender: Callable[[str], Any], *,
                 authorized=False, persist=True):
        """Trusted application invokes its approved sender exactly once.
        Sender returns its response in memory; not a provider-usage receipt.
        No HTTP route accepts a sender, callback, credential or destination.
        """
        if authorized is not True:
            raise PermissionError("Explicit permission to submit is required")
        if not callable(sender):
            raise TypeError("Sender must be callable")
        prepared = self.prepare(request, persist=False)
        response = prepared.response
        try:
            answer = sender(prepared.prompt)
        except Exception:
            response = _clear(response, "owned_sender_failed",
                              "Submission unconfirmed; no savings claimed and no automatic retry.")
            if persist:
                _record(response)
            return {"answer":None, "report":response.report.model_dump(mode="json"),
                    "submission_confirmed":False, "provider_savings_verified":False,
                    "model_consumption_verified":False}
        response.report.delivery_status = "owned_sender_returned"
        if persist:
            _record(response)
        return {"answer":answer, "report":response.report.model_dump(mode="json"),
                "submission_confirmed":False, "sender_returned":True,
                "original_prompt_estimate":prepared.original_prompt_estimate,
                "prepared_prompt_estimate":prepared.prepared_prompt_estimate,
                "provider_savings_verified":False, "model_consumption_verified":False}


def adapter_for_mcp(agent):
    if agent not in MCP_AGENTS:
        raise UnsupportedAdapter("Unsupported MCP client configuration")
    return AgentAdapter("mcp_"+agent)
