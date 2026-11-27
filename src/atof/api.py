from fastapi import FastAPI, HTTPException, Request
from urllib.parse import urlsplit
from .control import ControlSettings, snapshot, save_settings
from .models import OptimizeRequest, OptimizeResponse
from .registry import FeatureRegistry
from .service import optimize
from .reporting import applied_response

app=FastAPI(title='ATOF Phase 8',version='0.8.0')
DASHBOARD_REVISION = 'phase13-diagnostics-v10'
NO_CACHE_HEADERS = {'Cache-Control':'no-store, no-cache, must-revalidate, max-age=0',
                    'Pragma':'no-cache', 'Expires':'0',
                    'X-ATOF-Dashboard-Revision':DASHBOARD_REVISION}

@app.get('/health')
def health():
    return {'status':'ok','phase':8,'dashboard_revision':DASHBOARD_REVISION}

@app.get('/v1/features')
def features():
    catalog=FeatureRegistry().all()
    return {'count':len(catalog),'implemented_count':sum(f.implemented for f in catalog),'features':[vars(f) for f in catalog]}

@app.post('/v1/analyze',response_model=OptimizeResponse)
def analyze_request(payload:OptimizeRequest):
    payload=payload.model_copy(update={'execute':False})
    return optimize(payload)

@app.post('/v1/optimize',response_model=OptimizeResponse)
def optimize_request(payload:OptimizeRequest):
    return applied_response(optimize(payload))

@app.get('/v1/engines')
def engines():
    from .engines.registry import EngineRegistry
    supported = EngineRegistry().capabilities()
    return {'count':len(supported),'engines':[vars(item) for item in supported],
            'external_token_optimizer':'not_installed_license_review_required'}

@app.get('/v1/reporting/capabilities')
def reporting_capabilities():
    return {'estimate':'local_heuristic_estimate',
            'provider_usage':'unavailable_no_provider_receipt',
            'verified_token_savings':'requires_matched_provider_on_off_trials',
            'fidelity':'conservative_required_anchor_checks_not_semantic_equivalence',
            'retention':'in_memory_request_only_no_audit_database'}

@app.get('/v1/agents/capabilities')
def agent_capabilities():
    from .agent_capabilities import capabilities, AGENTS
    return {agent: capabilities(agent) for agent in AGENTS}

# Local unauthenticated developer dashboard: bind server to loopback only.
from fastapi.responses import HTMLResponse
from importlib.resources import files as package_files
from .analytics import history as analytics_history, summary as analytics_summary

@app.get('/dashboard',response_class=HTMLResponse,include_in_schema=False)
def dashboard():
    return HTMLResponse(package_files('atof').joinpath('ui/dashboard.html').read_text(encoding='utf-8'),
                        headers=NO_CACHE_HEADERS)

@app.get('/v1/analytics/history')
def dashboard_history(limit:int=50):
    return analytics_history(limit)

@app.get('/v1/analytics/summary')
def dashboard_summary(limit:int=200):
    return analytics_summary(limit)

# Phase 7: explicit user-selected text, not automatic interception.
from .ide import IDERequest, optimize_selection

@app.post('/v1/ide/optimize', response_model=OptimizeResponse)
def ide_optimize(request: IDERequest):
    return applied_response(optimize_selection(request))

@app.post('/v1/verification')
def verification():
    """Run synthetic fixtures; records local metadata only if enabled."""
    from .verify_platform import verify
    return verify()

@app.post('/v1/compare')
def compare_request(payload: OptimizeRequest):
    """Matched local evidence comparison; no model calls."""
    if payload.agent != 'custom_api':
        raise HTTPException(status_code=400, detail='Live agent comparisons require the actual agent integration')
    off = applied_response(optimize(payload.model_copy(update={'optimization_enabled':False, 'execute':True}), source_kind='developer_test'))
    on = applied_response(optimize(payload.model_copy(update={'optimization_enabled':True, 'execute':True}), source_kind='developer_test'))
    return {'off':off, 'on':on, 'measurement':'local_heuristic_estimate', 'provider_savings_verified':False}

@app.get('/v1/integrations/capabilities')
def integration_inventory():
    from .premodel import integration_capabilities
    return integration_capabilities()

@app.post('/v1/integrations/verify')
def verify_controlled_delivery():
    """Fixed synthetic evidence only; never invokes an external provider."""
    from .premodel import verify
    return verify()

@app.post('/v1/diagnostics/optimize', response_model=OptimizeResponse)
def diagnostic_optimize(payload: OptimizeRequest):
    return applied_response(optimize(payload, source_kind='developer_test'))

@app.get('/v1/dashboard/state')
def dashboard_state(request_id: str | None = None):
    from .feature_state import state
    return state(request_id)

@app.post('/v1/detect')
def detect_features(payload: OptimizeRequest):
    """Read-only planning diagnostics. No execution, storage or model calls."""
    from .detection import detect
    return detect(payload)

@app.post('/v1/verification/detection')
def verify_dynamic_detection():
    from .detection import verify_detection
    return verify_detection()

def _local_control_access(request: Request, *, write=False):
    # Browser writes must be same-origin and carry a non-simple custom header.
    # No cross-origin access or DNS-rebinding host names. Loopback only.
    try:
        host = urlsplit("//" + request.headers.get("host", "")).hostname
    except ValueError:
        host = None
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise HTTPException(403, "Local control endpoint requires a loopback host")
    origin = request.headers.get("origin")
    if origin and origin != str(request.base_url).rstrip("/"):
        raise HTTPException(403, "Cross-origin control access denied")
    if write and request.headers.get("x-atof-control") != "1":
        raise HTTPException(403, "Explicit local control header required")


@app.get('/v1/control')
def get_control(request: Request):
    _local_control_access(request)
    return snapshot()


@app.put('/v1/control')
def put_control(settings: ControlSettings, request: Request):
    _local_control_access(request, write=True)
    try:
        save_settings(settings)
    except (OSError, ValueError, __import__('sqlite3').Error):
        raise HTTPException(503, "Could not save local control settings") from None
    return snapshot()

@app.get('/v1/adapters')
def adapter_inventory():
    from .adapter_policy import inventory
    return {"adapters":inventory(), "automatic_interception_verified":False}


@app.post('/v1/adapters/{adapter_id}/prepare')
def prepare_adapter(adapter_id: str, payload: OptimizeRequest, request: Request):
    """Local owned-input preparation only; never forwards requests to providers."""
    from .adapters import AgentAdapter, UnsupportedAdapter
    _local_control_access(request)
    if request.headers.get("x-atof-adapter") != "1":
        raise HTTPException(403, "Explicit owned adapter header required")
    try:
        return AgentAdapter(adapter_id).prepare(payload).public()
    except UnsupportedAdapter:
        raise HTTPException(409, "Adapter does not support owned input preparation") from None
    except ValueError:
        raise HTTPException(400, "Invalid owned adapter request") from None

from pydantic import BaseModel, ConfigDict, StrictBool

class ControlSwitch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: StrictBool

@app.put('/v1/control/enabled')
def put_control_enabled(settings: ControlSwitch, request: Request):
    from .control import set_enabled
    _local_control_access(request, write=True)
    try:
        set_enabled(settings.enabled)
    except (OSError, ValueError, __import__('sqlite3').Error):
        raise HTTPException(503, "Could not save local control settings") from None
    return snapshot()


# Phase 9: browser-owned requests only. No extension-origin exemption.
from .browser import BrowserRequest
from fastapi.responses import Response

BROWSER_HEADERS = {
    **NO_CACHE_HEADERS,
    "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'",
    "X-Content-Type-Options":"nosniff",
    "Referrer-Policy":"no-referrer",
    "X-Frame-Options":"DENY",
}

@app.get('/browser',response_class=HTMLResponse,include_in_schema=False)
def browser_page(request: Request):
    _local_control_access(request)
    return HTMLResponse(package_files('atof').joinpath('ui/browser.html').read_text(encoding='utf-8'),headers=BROWSER_HEADERS)

@app.get('/browser/client.js',include_in_schema=False)
def browser_script(request: Request):
    _local_control_access(request)
    return Response(package_files('atof').joinpath('ui/browser.js').read_text(encoding='utf-8'),
                    media_type='application/javascript',headers=BROWSER_HEADERS)

@app.get('/v1/browser/status')
def browser_status(request: Request):
    _local_control_access(request)
    from .browser import status
    return status()

@app.post('/v1/browser/ask')
def browser_ask(payload: BrowserRequest, request: Request):
    _local_control_access(request)
    # Require actual same-origin browser request, explicit non-simple header
    # and JSON. No CORS, extension access, arbitrary URL, model or key fields.
    if (request.headers.get("origin") != str(request.base_url).rstrip("/") or
        request.headers.get("x-atof-browser") != "1" or
        request.headers.get("content-type","").split(";")[0].strip().lower() != "application/json" or
        request.headers.get("sec-fetch-site","same-origin") != "same-origin"):
        raise HTTPException(403,"Explicit same-origin browser request required")
    from .browser import ask
    try:
        return ask(payload)
    except PermissionError:
        raise HTTPException(403,"Browser provider disabled, unconfigured, or consent missing") from None
    except ValueError:
        raise HTTPException(400,"Invalid browser request") from None


from .structured import StructuredRequest

@app.get('/v1/features/readiness')
def feature_readiness():
    from .readiness import readiness
    return readiness()

@app.post('/v1/structured/optimize')
def structured_optimize(payload: StructuredRequest, request: Request):
    from .structured import optimize_structured
    _local_control_access(request)
    if request.headers.get("x-atof-structured") != "1":
        raise HTTPException(403,"Explicit structured caller header required")
    try:
        return optimize_structured(payload)
    except PermissionError:
        raise HTTPException(403,"Structured input authorization required") from None

@app.post('/v1/verification/structured')
def verify_structured_features():
    from .verify_structured import verify
    return verify()


@app.post('/v1/integrations/vscode-chat/optimize', response_model=OptimizeResponse)
def vscode_chat_optimize(payload: OptimizeRequest, request: Request):
    """Source retrieval tool; no provider call or native interception."""
    _local_control_access(request)
    if request.headers.get("x-atof-adapter") != "1":
        raise HTTPException(403, "Explicit local adapter header required")
    artifacts = [v for v in (payload.diff, payload.test_output, payload.error_output) if v]
    if (not ((1 <= len(payload.files) <= 8 and all(f.content for f in payload.files) and not artifacts)
             or (not payload.files and len(artifacts) == 1)) or
        sum(len(f.content.encode('utf-8')) for f in payload.files) + sum(len(v.encode('utf-8')) for v in artifacts) > 300000 or
        any((payload.context, payload.tool_output)) or
        payload.feature_override is not None or not payload.execute or payload.delivery_mode != "return_payload"):
        raise HTTPException(400, "Expected bounded authorized source files or one saved diagnostic artifact")
    return optimize(payload.model_copy(update={"agent":"copilot"}), transport="vscode_chat_tool", source_kind="agent_tool")


from typing import Literal
from uuid import UUID

class ClientReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    outcome: Literal["model_response_returned", "submission_unconfirmed"]

@app.post('/v1/integrations/vscode-owned/receipt')
def vscode_owned_receipt(payload: ClientReceipt, request: Request):
    """Advisory local client receipt; never upgrades native or provider verification."""
    _local_control_access(request)
    if request.headers.get("x-atof-adapter") != "1":
        raise HTTPException(403, "Explicit local adapter header required")
    from .analytics import client_receipt
    try:
        recorded = client_receipt(str(payload.request_id), payload.outcome)
    except (OSError, ValueError, __import__('sqlite3').Error):
        raise HTTPException(503, "Receipt storage unavailable") from None
    return {"recorded": recorded, "provider_savings_verified": False,
            "model_consumption_verified": False, "scope": "client_reported_only"}

@app.post('/v1/integrations/vscode-native/observe')
def vscode_native_observe(payload: OptimizeRequest, request: Request):
    """Prompt event observation only: no prompt replacement or evidence retrieval."""
    _local_control_access(request)
    if request.headers.get("x-atof-adapter") != "1":
        raise HTTPException(403, "Explicit local adapter header required")
    if any((payload.files,payload.diff,payload.test_output,payload.error_output,payload.context,payload.tool_output)):
        raise HTTPException(400,"Prompt observation accepts task only")
    if not snapshot().get("settings",{}).get("enabled") or not snapshot().get("available"):
        return {"observed":False,"reason":"disabled_or_unavailable"}
    result=optimize(OptimizeRequest(task=payload.task,agent="copilot",execute=False,delivery_mode="observe_only"),transport="vscode_chat_tool",source_kind="agent_tool",record_metrics=False)
    result.report.delivery_status="observed_only"
    from .analytics import record
    record(result)
    return {"observed":True,"request_id":result.report.request_id,"intent":result.report.intent,"model_consumption_verified":False}

class NativeReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID

@app.post('/v1/integrations/vscode-native/receipt')
def vscode_native_receipt(payload: NativeReceipt, request: Request):
    _local_control_access(request)
    if request.headers.get("x-atof-adapter") != "1":
        raise HTTPException(403,"Explicit local adapter header required")
    from .analytics import native_receipt
    return {"recorded":native_receipt(str(payload.request_id)),"model_consumption_verified":False,"provider_savings_verified":False}
