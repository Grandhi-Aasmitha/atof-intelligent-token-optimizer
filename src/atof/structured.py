"""Caller-owned, bounded structured context optimization.

No inferred authorization, implicit history access, persistence, provider calls
or execution of tools. Only declared optional units can be pruned. Batch
deduplication returns a caller-side expansion map; it does not claim avoided
provider calls. A task is always retained exactly.
"""
import json
import re
import uuid
from typing import Literal
from time import perf_counter
from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator
from .control import snapshot
from .legacy.tokens import estimate_text
from .models import OptimizationReport, OptimizeResponse, FeatureDecision

Kind = Literal["prompt_parts","history","memory","retrieval","handoff","state",
               "tool_schema","tool_search","embedding","duplicate_requests"]

FEATURE_BY_KIND = {
    "prompt_parts":"core.prompt",
    "history":"core.conversation_history",
    "memory":"core.memory",
    "retrieval":"core.rag_retrieval",
    "handoff":"agent.handoff",
    "state":"agent.state",
    "tool_schema":"agent.tool_schema",
    "tool_search":"advanced.tool_search",
    "embedding":"enterprise.embedding",
    "duplicate_requests":"enterprise.duplicate_request",
}
STRUCTURED_FEATURES = frozenset(FEATURE_BY_KIND.values()) | {"core.token_budget","advanced.compaction"}

class Unit(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(min_length=1,max_length=128)
    text: str = Field(max_length=100000)
    optional: StrictBool = False
    score: float = Field(default=1.0,ge=0,le=1,allow_inf_nan=False)
    superseded_by: str | None = Field(default=None,max_length=128)

class StructuredRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task: str = Field(min_length=1,max_length=20000)
    kind: Kind
    items: list[Unit] = Field(min_length=1,max_length=128)
    authorized: StrictBool = False
    optimization_enabled: StrictBool = True
    allow_pruning: StrictBool = False
    allow_deduplication: StrictBool = False
    # Batch input is explicitly one scope/model/configuration; no cache.
    idempotent_batch: StrictBool = False
    allowed_ids: list[str] | None = Field(default=None,max_length=128)
    min_score: float | None = Field(default=None,ge=0,le=1,allow_inf_nan=False)
    top_k: int | None = Field(default=None,ge=1,le=128)
    token_budget: int | None = Field(default=None,ge=64,le=200000)
    compaction_trigger: int | None = Field(default=None,ge=64,le=200000)
    previous_estimate: int | None = Field(default=None,ge=0,le=10000000)

    @model_validator(mode="after")
    def validate_units(self):
        ids=[x.id for x in self.items]
        if len(set(ids))!=len(ids):
            raise ValueError("Duplicate unit IDs")
        if sum(len(x.text)+len(x.id) for x in self.items)>500000:
            raise ValueError("Combined evidence too large")
        if not self.task.strip():
            raise ValueError("Task required")
        if self.allowed_ids is not None and not set(self.allowed_ids).issubset(ids):
            raise ValueError("Unknown allowed ID")
        if any(x.superseded_by is not None and (x.superseded_by not in ids or x.superseded_by==x.id) for x in self.items):
            raise ValueError("Invalid supersession reference")
        return self

def wire(task,items):
    # Exact task and retained unit content; metadata and maps stay caller-side.
    return json.dumps({"task":task,"items":[{"id":x.id,"text":x.text} for x in items]},
                      ensure_ascii=False,separators=(",",":"))

def tokens(task,items):
    return estimate_text(wire(task,items))

def lexical_score(task,text):
    terms=set(re.findall(r"\w+",task.casefold()))
    return len(terms.intersection(re.findall(r"\w+",text.casefold())))

def complexity(task, items, count):
    # Heuristic only, not a model-routing decision.
    return "large" if count>16000 or len(items)>50 else "medium" if count>2000 or len(items)>10 else "small"

def optimize_structured(request: StructuredRequest, *, persist=True, diagnostic=False):
    if not request.authorized:
        raise PermissionError("Explicit authorization required")
    start=perf_counter()
    original=list(request.items)
    items=list(original)
    mapping={x.id:x.id for x in original}
    before=tokens(request.task,original)
    stages=[]
    state=snapshot() if not diagnostic else {"available":True,"settings":{"enabled":True}}
    enabled=state["available"] and state["settings"]["enabled"] and request.optimization_enabled
    policy=("diagnostic" if diagnostic else "settings_unavailable" if not state["available"] else
            "disabled" if not state["settings"]["enabled"] else "request_disabled" if not request.optimization_enabled else "enabled")
    protected={x.id for x in original if not x.optional}
    # In a history bundle each unit is a complete caller-supplied turn group.
    # Always preserve latest and any supersession target. No cycle deletion.
    if request.kind=="history":
        protected.add(original[-1].id)
        protected.update(x.superseded_by for x in original if x.superseded_by)
    allowed=set(request.allowed_ids or [])
    if request.allowed_ids is not None:
        protected.update(allowed)
    if request.kind in ("embedding","duplicate_requests"):
        # These are set-like jobs with a caller-side fan-out map, not history.
        protected=set()
    def accept(feature,candidate,aliases=None):
        nonlocal items,mapping
        old={x.id:x for x in items}
        ids={x.id for x in candidate}
        if not candidate or len(ids)!=len(candidate) or not protected.issubset(ids):
            return False
        if any(x.id not in old or x!=old[x.id] for x in candidate):
            return False
        if [x.id for x in items if x.id in ids]!=[x.id for x in candidate]:
            return False
        removed=set(old)-ids
        aliases=aliases or {}
        if any(k not in removed or v not in ids or old[k].text!=old[v].text for k,v in aliases.items()):
            return False
        if any(not old[k].optional and k not in aliases for k in removed):
            return False
        if request.kind in ("embedding","duplicate_requests") and removed!=set(aliases):
            return False
        a,b=tokens(request.task,items),tokens(request.task,candidate)
        if b>=a:
            return False
        for key,value in list(mapping.items()):
            if value in removed:
                mapping[key]=aliases.get(value)
        stages.append({"feature_id":feature,"before":a,"after":b,"removed":a-b})
        items=candidate
        return True

    def prune(feature,drop):
        if request.allow_pruning:
            accept(feature,[x for x in items if x.id not in drop or x.id in protected])

    def trim_budget(feature, budget, eligible):
        if not request.allow_pruning:
            return
        remaining=list(items)
        for x in sorted((i for i in items if i.id in eligible and i.id not in protected and i.optional),
                        key=lambda i:(i.score,original.index(i))):
            if tokens(request.task,remaining)<=budget:
                break
            if len(remaining)>1:
                remaining=[i for i in remaining if i.id!=x.id]
        accept(feature,remaining)

    if enabled:
        feature=FEATURE_BY_KIND[request.kind]
        kind=request.kind
        if kind in ("prompt_parts","embedding","duplicate_requests") and request.allow_deduplication and (
                kind!="duplicate_requests" or request.idempotent_batch):
            seen={}
            aliases={}
            for x in items:
                if x.text in seen and (kind!="prompt_parts" or (x.optional and x.id not in protected)):
                    aliases[x.id]=seen[x.text]
                else:
                    seen.setdefault(x.text,x.id)
            accept(feature,[x for x in items if x.id not in aliases],aliases)
        elif kind=="history":
            eligible={x.id for x in items if x.optional and x.superseded_by in {i.id for i in items}}
            if request.compaction_trigger is not None and before>request.compaction_trigger:
                trim_budget("advanced.compaction",request.compaction_trigger,eligible)
            else:
                prune(feature,eligible)
        elif kind=="memory" and request.min_score is not None:
            prune(feature,{x.id for x in items if x.optional and x.score<request.min_score})
        elif kind in ("retrieval","tool_search") and request.top_k is not None:
            rank=lambda x: (x.score if kind=="retrieval" else lexical_score(request.task,x.text),x.score)
            ranked=sorted((x for x in items if x.id not in protected),key=rank,reverse=True)
            keep=protected | {x.id for x in ranked[:max(0,request.top_k-len(protected))]}
            prune(feature,{x.id for x in items if x.id not in keep})
        elif kind in ("handoff","state","tool_schema") and request.allowed_ids is not None:
            prune(feature,{x.id for x in items if x.id not in allowed and x.optional})
        if request.token_budget is not None and kind not in ("embedding","duplicate_requests","history"):
            trim_budget("core.token_budget",request.token_budget,{x.id for x in items})
    after=tokens(request.task,items)
    used=[s["feature_id"] for s in stages]
    report=OptimizationReport(request_id=str(uuid.uuid4()),intent="structured_"+request.kind,
        agent="custom_api",original_estimated_tokens=before,
        optimized_estimated_tokens=after if used else None,
        estimated_reduction_tokens=before-after if used else None,
        estimated_reduction_percent=round(100*(before-after)/before,2) if used and before else None,
        decisions=[FeatureDecision(feature_id=s["feature_id"],status="executed",reason="authorized_structured_reduction",estimated_before=s["before"],estimated_after=s["after"]) for s in stages],
        executed_features=used,executed_feature=used[0] if used else None,
        engine="StructuredOptimizer" if used else None,
        execution_transport="structured_api",source_kind="synthetic_test" if diagnostic else "structured_api",
        delivery_status="payload_returned_to_client" if used else "not_attempted",
        fidelity_status="passed" if used else "not_evaluated",control_policy=policy,
        execution_duration_ms=round((perf_counter()-start)*1000,3),
        token_budget=request.token_budget)
    result=OptimizeResponse(optimized_context=wire(request.task,items) if used else None,report=report)
    if persist:
        from .adapters import _record
        _record(result)
    return {"task":request.task,"items":[x.model_dump() for x in items],
            "id_map":mapping,"prepared_input":wire(request.task,items),
            "before":before,"after":after,"estimated_reduction":before-after,
            "budget_met":None if request.token_budget is None else after<=request.token_budget,
            "complexity":complexity(request.task,original,before),
            "context_growth":None if request.previous_estimate is None else before-request.previous_estimate,
            "stages":stages,"report":report.model_dump(mode="json"),
            "caller_must_apply":True,"provider_savings_verified":False,
            "model_consumption_verified":False}
