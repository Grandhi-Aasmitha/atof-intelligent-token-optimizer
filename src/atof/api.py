from fastapi import FastAPI
from .models import OptimizeRequest, OptimizeResponse
from .registry import FeatureRegistry
from .service import optimize

app=FastAPI(title='ATOF Phase 4',version='0.4.0')

@app.get('/health')
def health():
    return {'status':'ok','phase':4}

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
    return optimize(payload)

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
