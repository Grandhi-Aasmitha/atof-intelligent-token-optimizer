from fastapi import FastAPI
from .models import OptimizeRequest, OptimizeResponse
from .registry import FeatureRegistry
from .service import optimize

app=FastAPI(title='ATOF Phase 1',version='0.1.0')

@app.get('/health')
def health():
    return {'status':'ok','phase':1}

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
