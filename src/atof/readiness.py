"""Complete catalog readiness: working boundaries, not fabricated activation."""
from .registry import FeatureRegistry
from .engines.registry import EngineRegistry
from .structured import STRUCTURED_FEATURES

CONTROLS = {
    "intelligent.task_complexity":"Structured workload size heuristic, not semantic difficulty",
    "governance.token_counting":"Local deterministic token estimator",
    "governance.policy":"Shared ON/OFF, eligibility and transport gates",
    "governance.analytics":"Opt-in metadata-only request history and estimates",
    "governance.evaluation":"Offline fixture and dynamic detection verification",
    "advanced.fidelity":"Per-stage anchors and conservative structural validation",
    "advanced.context_growth":"Caller-supplied previous estimate vs current structured input",
}
BLOCKERS = {
    "core.semantic_compression":"Semantic equivalence and quality evaluation beyond current deterministic validators",
    "core.prompt_caching":"Provider-supported cache controls and verified cache usage",
    "core.response_cache":"Isolated cache key, freshness, identity, permission and response validity",
    "core.output_token":"Provider-specific output constraints and quality evaluation",
    "intelligent.model_routing":"Approved model allowlist, comparable capabilities, costs and live routing",
    "intelligent.llm_call":"Owned orchestration and idempotent call-elimination proof",
    "intelligent.reasoning_effort":"Provider-supported reasoning controls and matched quality trials",
    "intelligent.adaptive":"Verified feedback loop and per-task strategy learning",
    "intelligent.token_cost":"Current approved provider rates and usage receipts",
    "agent.loop":"Owned agent execution loop with termination and recovery contract",
    "agent.tool_call":"Owned tool runtime, permission and side-effect semantics",
    "coding.incremental_context":"Verified prior delivery, session correlation and reconstruction",
    "enterprise.batch_request":"Provider batch submission, result correlation and retry contract",
    "enterprise.structured_output":"Provider-enforced schema and output fidelity validation",
    "enterprise.multimodal":"Authorized media pipeline and modality-specific counting",
    "enterprise.quality_aware":"Measured semantic/task quality gate across matched model trials",
    "enterprise.dynamic_cache":"Isolated cache lifecycle, eviction and invalidation",
    "enterprise.continuous_learning":"Approved feedback dataset and safe evaluation/promotion",
    "advanced.tool_clearing":"Verified tool-result lifetime and dependency-aware clearing",
    "advanced.persistent_memory":"Authorized persistent memory store, TTL and access isolation",
    "advanced.cache_aware_clearing":"Provider cache boundary and invalidation proof",
    "advanced.programmatic_tool":"Owned tool execution sandbox, authorization and side-effect controls",
}
def readiness(*, registry=None, engines=None):
    registry=registry if registry is not None else FeatureRegistry()
    engines=engines if engines is not None else EngineRegistry()
    rows=[]
    for f in registry.all():
        if engines.supports(f.id):
            state,scope="text_engine","Existing structured text evidence pipeline"
        elif f.id in STRUCTURED_FEATURES:
            state,scope="structured_candidate","Caller-owned typed input; adapter must apply result"
        elif f.id in CONTROLS:
            state,scope="control",CONTROLS[f.id]
        else:
            state,scope="runtime_required",BLOCKERS.get(f.id,"No registered implementation")
        rows.append({"id":f.id,"name":f.name,"readiness":state,"scope":scope,
                     "native_replacement_verified":False,"provider_savings_verified":False})
    counts={key:sum(r["readiness"]==key for r in rows) for key in ("text_engine","structured_candidate","control","runtime_required")}
    return {"total":len(rows),"counts":counts,"features":rows,"provider_savings_verified":False}
