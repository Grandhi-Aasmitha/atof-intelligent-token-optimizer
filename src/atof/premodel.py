"""Phase 1: trusted, explicit pre-model adapter. No interception or remote service."""
from dataclasses import dataclass, asdict
from hashlib import sha256
from typing import Protocol
import json
import sqlite3

from .analytics import record
from .legacy.tokens import estimate_text
from .models import OptimizeRequest, OptimizeResponse
from .orchestrator import compose, source_sections
from .reporting import applied_response
from .service import optimize


@dataclass(frozen=True)
class DeliveryReceipt:
    submitted_sha256: str
    receiver_sha256: str | None = None
    provider_observation: dict | None = None


class Receiver(Protocol):
    """Trusted downstream adapter, not a caller-supplied URL or agent label."""
    def deliver(self, prompt: str) -> DeliveryReceipt: ...


def digest(prompt: str) -> str:
    return sha256(prompt.encode("utf-8")).hexdigest()


def assemble(task: str, evidence: str) -> str:
    # JSON framing preserves the exact task and keeps evidence separate.
    return json.dumps({"task": task, "evidence": evidence}, ensure_ascii=False,
                      separators=(",", ":"))


class LocalReceiptReceiver:
    """Offline stand-in for a downstream model input boundary; no model call."""
    def deliver(self, prompt: str) -> DeliveryReceipt:
        return DeliveryReceipt(digest(prompt), digest(prompt))


class ProviderReceiver:
    """Use an existing, explicitly configured provider client. No automatic retries."""
    def __init__(self, provider, required_terms=()):
        self.provider = provider
        self.required_terms = tuple(required_terms)

    def deliver(self, prompt: str) -> DeliveryReceipt:
        observation = self.provider.generate(prompt, self.required_terms)
        return DeliveryReceipt(digest(prompt), provider_observation=asdict(observation))


def integration_capabilities():
    """Static contract inventory, never inferred live installation or compatibility."""
    return {
        "catalog_scope": 48,
        "adapters": [
            {"id": "controlled_local", "agent": "custom_api", "environment": "local test",
             "status": "available_for_validation", "scope": "owned prompt assembly and delivery to offline receiver",
             "live_agent_verified": False},
            {"id": "controlled_provider", "agent": "custom_api", "environment": "approved provider API",
             "status": "opt_in_validation_required", "scope": "owned request to explicitly configured provider",
             "live_agent_verified": False},
            *[{"id": "mcp_" + agent, "agent": agent, "environment": "compatible MCP client",
               "status": "explicit_tool_only", "scope": "caller-supplied evidence; replacement not proven",
               "live_agent_verified": False} for agent in ("copilot", "codex", "claude")],
            *[{"id": ident, "agent": agent, "environment": ide,
               "status": "unverified", "scope": "requires approved runtime-specific replacement test",
               "live_agent_verified": False} for ident, agent, ide in (
                   ("intellij_copilot", "copilot", "IntelliJ IDEA"),
                   ("intellij_ai", "jetbrains_ai", "IntelliJ IDEA"),
                   ("vscode_copilot", "copilot", "VS Code"),
                   ("vscode_codex", "codex", "VS Code"),
                   ("vscode_claude", "claude", "VS Code"),
                   ("chatgpt_web", "chatgpt", "Web"),
                   ("other_agent", "other", "Other"))]
        ],
        "automatic_interception_verified": False,
        "provider_savings_verified": False,
    }


def _fallback(response):
    report = response.report.model_copy(update={
        "optimized_estimated_tokens": None, "estimated_reduction_tokens": None,
        "estimated_reduction_percent": None, "executed_features": [],
        "executed_feature": None, "engine": None, "decisions": [],
        "stage_results": [], "fidelity_checks": [],
        "warnings": ["Original authorized evidence retained; no accepted delivered reduction."],
    })
    return OptimizeResponse(report=report)


def deliver(request: OptimizeRequest, receiver: Receiver, *, authorized: bool = False,
            persist: bool = True) -> dict:
    """Optimize before an owned downstream call. Never pass original alongside candidate."""
    if not authorized:
        raise PermissionError("Explicit authorization required")
    if request.agent != "custom_api" or not request.execute or request.delivery_mode != "return_payload":
        raise ValueError("Controlled adapter requires an executing custom_api request")
    original = compose(source_sections(request))
    original_prompt = assemble(request.task, original)
    response = applied_response(optimize(request, record_metrics=False))
    candidate = response.optimized_context
    # Be conservative for partially rejected candidates and account for framing.
    prompt = assemble(request.task, candidate) if candidate else original_prompt
    if (not candidate or response.report.fidelity_status != "passed"
            or estimate_text(prompt) >= estimate_text(original_prompt)):
        response = _fallback(response)
        prompt = original_prompt
    receipt = None
    failure = None
    try:
        receipt = receiver.deliver(prompt)
        if not isinstance(receipt, DeliveryReceipt) or receipt.submitted_sha256 != digest(prompt):
            raise ValueError("Invalid submission receipt")
        if receipt.receiver_sha256 is not None and receipt.receiver_sha256 != digest(prompt):
            raise ValueError("Receiver digest mismatch")
        if receipt.receiver_sha256 is None and receipt.provider_observation is None:
            raise ValueError("Missing downstream receipt")
        status = ("controlled_receiver_confirmed" if receipt.receiver_sha256 is not None
                  else "controlled_provider_response_returned")
    except Exception:
        # No retry after an ambiguous downstream failure (may have incurred cost).
        response = _fallback(response)
        receipt = None
        failure = "Downstream delivery not confirmed; no savings claimed."
        status = "controlled_delivery_failed"
    report = response.report
    report.execution_transport = "controlled_adapter"
    report.delivery_status = status
    if receipt is not None and receipt.provider_observation is not None:
        report.provider_usage = receipt.provider_observation
    if failure:
        report.warnings.append(failure)
    if persist:
        try:
            record(response)
        except (OSError, ValueError, RuntimeError, sqlite3.Error):
            pass
    return {
        "report": report.model_dump(mode="json"),
        "delivery": asdict(receipt) if receipt else None,
        "original_prompt_estimate": estimate_text(original_prompt),
        "delivered_prompt_estimate": estimate_text(prompt) if receipt else None,
        "prompt_estimated_reduction": (estimate_text(original_prompt) - estimate_text(prompt)) if receipt else None,
        "measurement": "local_heuristic_estimate_including_json_framing",
        "model_consumption_verified": False,
        "provider_savings_verified": False,
        "failure": failure,
    }


def compare(request: OptimizeRequest, receiver: Receiver, *, authorized: bool = False,
            order: str = "AB", persist: bool = True):
    if order not in ("AB", "BA"):
        raise ValueError("Invalid arm order")
    arms = {}
    for arm in order:
        arms[arm] = deliver(request.model_copy(update={"optimization_enabled": arm == "B"}),
                            receiver, authorized=authorized, persist=persist)
        if arms[arm]["delivery"] is None:
            break
    off, on = arms.get("A"), arms.get("B")
    complete = bool(off and on and off["delivery"] and on["delivery"])
    before = off["delivered_prompt_estimate"] if complete else None
    after = on["delivered_prompt_estimate"] if complete else None
    return {
        "off": off, "on": on, "order": order, "complete": complete,
        "full_prompt_before": before, "full_prompt_after": after,
        "full_prompt_estimated_reduction": before - after if complete else None,
        "full_prompt_estimated_reduction_percent": round(100 * (before-after)/before, 2) if complete and before else None,
        "provider_savings_verified": False,
    }


def fixture():
    return OptimizeRequest(task="Identify the cause of the synthetic application failure.",
                           error_output="heartbeat ok\n" * 150 + "RuntimeError: database unavailable")


def verify():
    result = compare(fixture(), LocalReceiptReceiver(), authorized=True)
    off, on = result["off"], result["on"]
    result["passed"] = bool(result["complete"] and result["full_prompt_estimated_reduction"] > 0
                            and not off["report"]["executed_features"]
                            and on["report"]["executed_features"]
                            and off["delivery"]["receiver_sha256"] != on["delivery"]["receiver_sha256"])
    result["scope"] = "offline controlled receiver; no live IDE or model calls"
    return result


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Phase 1 controlled delivery validation; synthetic evidence only")
    parser.add_argument("--provider", choices=("offline", "openai", "gemini"), default="offline")
    parser.add_argument("--model")
    parser.add_argument("--accept-paid-calls", action="store_true")
    parser.add_argument("--order", choices=("AB", "BA"), default="AB")
    args = parser.parse_args(argv)
    if args.provider == "offline":
        result = compare(fixture(), LocalReceiptReceiver(), authorized=True, order=args.order)
    else:
        if not args.accept_paid_calls or not args.model:
            parser.error("Real provider validation requires approved credentials, --model and --accept-paid-calls")
        from .benchmark import OpenAIResponsesProvider, GeminiGenerateContentProvider, ProviderError
        try:
            factory = OpenAIResponsesProvider if args.provider == "openai" else GeminiGenerateContentProvider
            receiver = ProviderReceiver(factory(args.model), ("database unavailable",))
            result = compare(fixture(), receiver, authorized=True, order=args.order)
        except (ProviderError, ValueError) as exc:
            parser.error(str(exc))
    print(json.dumps(result, indent=2))
    return 0 if result["complete"] and result["full_prompt_estimated_reduction"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
