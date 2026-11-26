from fastapi import FastAPI, HTTPException
from .models import OptimizeRequest, OptimizeResponse
from .registry import FeatureRegistry
from .service import optimize
from .reporting import applied_response

app=FastAPI(title='ATOF Phase 8',version='0.8.0')

@app.get('/health')
def health():
    return {'status':'ok','phase':8}

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
    from .agent_capabilities import capabilities
    return {agent: capabilities(agent) for agent in ('custom_api', 'codex', 'copilot', 'claude')}

# Local unauthenticated developer dashboard: bind server to loopback only.
from fastapi.responses import HTMLResponse
from importlib.resources import files as package_files
from .analytics import history as analytics_history, summary as analytics_summary

@app.get('/dashboard',response_class=HTMLResponse,include_in_schema=False)
def dashboard():
    return package_files('atof').joinpath('ui/dashboard.html').read_text(encoding='utf-8')

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
