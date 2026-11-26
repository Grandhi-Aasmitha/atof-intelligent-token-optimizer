"""One catalog projection and metadata-only dashboard state, shared by all clients."""
from .registry import FeatureRegistry
from .engines.registry import EngineRegistry
from .adapter_policy import can_return_candidate
from .analytics import history

SOURCE_LABELS = {
    "agent_tool": "Agent tool (not verified live)",
    "owned_adapter": "Owned API request (not verified live)",
    "structured_api": "Structured candidate (caller must apply)",
    "local_api": "Local request",
    "developer_test": "Developer test",
    "synthetic_test": "Synthetic test",
    "controlled_validation": "Controlled test",
    "legacy_unknown": "Earlier record (source unknown)",
}

def feature_states(record=None, *, registry=None, engines=None):
    registry = registry if registry is not None else FeatureRegistry()
    engines = engines if engines is not None else EngineRegistry()
    record = record or {}
    used = {f["id"] for f in record.get("features", []) if f.get("status") == "executed"}
    agent = record.get("agent")
    transport = record.get("transport")
    supported = (agent is None or
                 (transport == "controlled_adapter" and agent == "custom_api") or
                 can_return_candidate(agent, transport, "return_payload"))
    from .readiness import readiness
    readiness_by_id = {x['id']:x for x in readiness(registry=registry, engines=engines)['features']}
    result = []
    for f in registry.all():
        executable = f.implemented and engines.supports(f.id)
        info = readiness_by_id.get(f.id, {})
        level = info.get('readiness','runtime_required')
        structured = level == 'structured_candidate'
        active = (executable and supported or structured and transport == 'structured_api') and f.id in used
        status = ('used' if active else 'structured_available' if structured else 'control_available' if level == 'control' else
                  'planned' if not executable else 'available' if supported else 'unavailable_for_agent')
        result.append({"id":f.id, "name":f.name, "classification":f.classification,
                       "implemented":f.implemented, "executable":executable,
                       "supported_for_agent":(supported if executable else structured and transport == "structured_api"),
                       "used":active, "state":status, "readiness":level, "scope":info.get("scope","")})
    return result


def present(record):
    item = dict(record)
    kind = item.get("source_kind", "legacy_unknown")
    item["source_label"] = SOURCE_LABELS.get(kind, SOURCE_LABELS["legacy_unknown"])
    item["live_verified"] = False  # No native verified delivery path in this release.
    delivery = item["delivery_status"]
    item["delivery_label"] = {
        "controlled_receiver_confirmed":"Offline receiver confirmed",
        "controlled_provider_response_returned":"Controlled provider responded (test)",
        "controlled_delivery_failed":"Delivery failed",
        "owned_payload_prepared":"Input prepared; submission unverified",
        "owned_sender_returned":"Owned sender returned; model usage unverified",
        "owned_sender_failed":"Submission unconfirmed",
        "mcp_tool_result_returned":"Candidate returned to agent tool",
        "payload_returned_to_client":"Candidate created",
        "observed_only":"Observed only",
        "not_attempted":"No optimized candidate",
    }.get(delivery, "Delivery unverified")
    return item


def state(request_id=None):
    data = history(200)
    records = [present(r) for r in data["records"]]
    # Legacy records may be synthetic; never assume live from agent label.
    agent_records = [r for r in records if r["source_kind"] in ("agent_tool","owned_adapter","structured_api")]
    latest = agent_records[0] if agent_records else None
    selected = next((r for r in records if r["request_id"] == request_id), None) if request_id else latest
    features = feature_states(selected)
    return {
        "service":{"status":"running", "analytics_enabled":data["enabled"]},
        "connection":{"status":"unverified", "label":"No verified live AI connection",
                      "latest_agent_tool":latest["agent"] if latest else None},
        "latest":latest, "selected":selected, "features":features,
        "feature_counts":{"total":len(features), "implemented":sum(f["executable"] for f in features),
                          "used":sum(f["used"] for f in features)},
        "history":records, "provider_savings_verified":False,
        "readiness_counts":{k:sum(f["readiness"]==k for f in features) for k in ("text_engine","structured_candidate","control","runtime_required")},
    }
