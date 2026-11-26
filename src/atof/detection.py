"""Read-only dynamic detection and unforced synthetic validation."""
from .analyzer import analyze
from .engines.registry import EngineRegistry
from .registry import FeatureRegistry
from .planner import select
from .models import OptimizeRequest


def detect(request: OptimizeRequest, *, transport="http_api", registry=None, engines=None):
    registry = registry if registry is not None else FeatureRegistry()
    engines = engines if engines is not None else EngineRegistry()
    analysis = analyze(request)
    decisions = select(request, analysis, registry, engines, transport=transport)
    return {"intent":analysis.intent,
            "supplied_evidence":sorted(analysis.supplied_slots),
            "requested_evidence":sorted(analysis.requested_slots),
            "missing_evidence":sorted(analysis.requested_slots-analysis.supplied_slots),
            "catalog_count":len(registry.all()), "registered_count":len(engines.capabilities()),
            "selected_features":[d.feature_id for d in decisions if d.status=="selected"],
            "decisions":[d.model_dump() for d in decisions],
            "optimization_enabled":request.optimization_enabled,
            "executed":False, "provider_savings_verified":False}


def verify_detection():
    """Reuse all executable fixture types, without forcing a feature."""
    from .verify_platform import fixtures
    from .service import optimize
    from .reporting import applied_response
    results = []
    for feature, data, anchors in fixtures():
        request = OptimizeRequest(**data)
        plan = detect(request)
        off = optimize(request.model_copy(update={"optimization_enabled":False}), source_kind="synthetic_test")
        on = applied_response(optimize(request, source_kind="synthetic_test"))
        r = on.report
        passed = (feature in plan["selected_features"]
                  and r.executed_features == [feature] and not off.report.executed_features
                  and off.optimized_context is None
                  and r.original_estimated_tokens == off.report.original_estimated_tokens
                  and (r.estimated_reduction_tokens or 0) > 0
                  and all(a in (on.optimized_context or "") for a in anchors))
        results.append({"feature":feature, "passed":passed, "before":r.original_estimated_tokens,
                        "after":r.optimized_estimated_tokens, "removed":r.estimated_reduction_tokens,
                        "fidelity":r.fidelity_status, "request_id":r.request_id})
    return {"passed":sum(x["passed"] for x in results), "total":len(results),
            "results":results, "measurement":"local_heuristic_estimate",
            "provider_savings_verified":False}


def main():
    import json
    result = verify_detection()
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] == result["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
