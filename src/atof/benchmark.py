"""Paired OFF/ON provider usage observations; no causal-savings claim."""
from dataclasses import dataclass, asdict
from hashlib import sha256
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from typing import Protocol
import json, os, time, re

from .models import OptimizeRequest
from .orchestrator import compose, source_sections
from .service import optimize
from .reporting import applied_response
from .legacy.tokens import estimate_text

class ProviderError(RuntimeError): pass

@dataclass(frozen=True)
class ProviderObservation:
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int | None
    latency_ms: float
    output_sha256: str
    required_terms_present: bool
    receipt_source: str

class Provider(Protocol):
    name: str
    model: str
    def generate(self,text: str,required_terms:tuple[str,...])->ProviderObservation: ...

def _observe(text, terms, before, after, cached, ms, source):
    if any(not isinstance(v,int) or v<0 for v in (before,after)):
        raise ProviderError('Provider token receipt missing or invalid')
    if cached is not None and (not isinstance(cached,int) or cached<0 or cached>before):
        raise ProviderError('Invalid cache receipt')
    return ProviderObservation(before,after,cached,round(ms,2),sha256(text.encode('utf-8')).hexdigest(),
        all(t.casefold() in text.casefold() for t in terms),source)

def _post_json(url,data,headers):
    try:
        req=Request(url, data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type':'application/json',**headers}, method='POST')
        with urlopen(req,timeout=60) as response:
            if response.status!=200: raise ProviderError('Unexpected provider response status')
            result=json.loads(response.read(10_000_000).decode('utf-8'))
        if not isinstance(result,dict): raise ProviderError('Malformed provider response')
        return result
    except (URLError,HTTPError,TimeoutError,ValueError):
        raise ProviderError('Provider request failed; check credentials and access') from None

class OpenAIResponsesProvider:
    name='openai'
    def __init__(self,model,api_key=None):
        self.model=model
        self.api_key=api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key: raise ProviderError('OPENAI_API_KEY missing')
    def generate(self,text,required_terms):
        started=time.perf_counter()
        r=_post_json('https://api.openai.com/v1/responses',
            {'model':self.model,'input':text,'max_output_tokens':256,'store':False},
            {'Authorization':'Bearer '+self.api_key})
        if r.get('status')!='completed': raise ProviderError('Incomplete response')
        usage=r.get('usage') or {}
        output='\n'.join(c.get('text','') for item in r.get('output',[])
            if item.get('type')=='message' for c in item.get('content',[]) if c.get('type')=='output_text')
        return _observe(output,required_terms,usage.get('input_tokens'),usage.get('output_tokens'),
            (usage.get('input_tokens_details') or {}).get('cached_tokens'),
            (time.perf_counter()-started)*1000,'openai.responses.usage')

class GeminiGenerateContentProvider:
    name='gemini'
    def __init__(self,model,api_key=None):
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}',model):
            raise ValueError('Invalid Gemini model')
        self.model=model
        self.api_key=api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key: raise ProviderError('GEMINI_API_KEY missing')
    def generate(self,text,required_terms):
        started=time.perf_counter()
        r=_post_json('https://generativelanguage.googleapis.com/v1beta/models/'+self.model+':generateContent',
            {'contents':[{'role':'user','parts':[{'text':text}]}],
             'generationConfig':{'maxOutputTokens':256,'temperature':0}},
            {'x-goog-api-key':self.api_key})
        usage=r.get('usageMetadata') or {}
        output='\n'.join(p.get('text','') for c in r.get('candidates',[])
            for p in (c.get('content') or {}).get('parts',[]) if 'text' in p)
        return _observe(output,required_terms,usage.get('promptTokenCount'),usage.get('candidatesTokenCount'),
            usage.get('cachedContentTokenCount'),(time.perf_counter()-started)*1000,
            'gemini.generateContent.usageMetadata')

class SyntheticProvider:
    name='synthetic'
    model='synthetic-not-billed'
    def generate(self,text,required_terms):
        return _observe('Synthetic reply: '+', '.join(required_terms),required_terms,
            estimate_text(text),12,0,0.0,'synthetic_not_provider_measured')

def _prompt(task,context):
    return f'Task:\n{task}\n\nEvidence:\n{context}\n\nUse the evidence to answer concisely.'

def benchmark(request: OptimizeRequest,provider:Provider,*,required_terms=(),order='AB'):
    if order not in ('AB','BA'): raise ValueError('Invalid arm order')
    if request.agent!='custom_api': raise ValueError('Only controlled API requests are benchmarkable')
    baseline=compose(source_sections(request))
    if not baseline: raise ValueError('Missing evidence')
    response=optimize(request, source_kind='synthetic_test' if provider.name == 'synthetic' else 'developer_test')
    if not response.optimized_context:
        return {'status':'no_reducing_candidate','provider_calls':0,'report':applied_response(response).report.model_dump(mode='json')}
    prompts={'A':_prompt(request.task,baseline),'B':_prompt(request.task,response.optimized_context)}
    results={arm:provider.generate(prompts[arm],tuple(required_terms)) for arm in order}
    a,b=results['A'],results['B']
    measured=all(v.receipt_source!='synthetic_not_provider_measured' for v in (a,b))
    return {'status':'completed','provider_calls':2,'provider':provider.name,'model':provider.model,
        'order':order,'baseline':asdict(a),'optimized':asdict(b),
        'provider_usage_measured':measured,
        'quality_gate_passed':a.required_terms_present and b.required_terms_present,
        'task_quality_gate':'required_terms_only_not_semantic_equivalence',
        'input_token_difference':a.input_tokens-b.input_tokens if measured else None,
        'total_token_difference':(a.input_tokens+a.output_tokens)-(b.input_tokens+b.output_tokens) if measured else None,
        'estimated_context_reduction':response.report.estimated_reduction_tokens,
        'provider_savings_verified':False,
        'features_executed':response.report.executed_features,
        'caveat':'Paired observations, not causal savings. Repeat AB/BA with matched cache conditions and quality review.'}
