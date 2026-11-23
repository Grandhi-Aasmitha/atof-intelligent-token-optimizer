"""Phase 8 provider receipt validation, synthetic A/B and safe paid-call gating."""
import pytest
from atof.benchmark import (SyntheticProvider,OpenAIResponsesProvider,
   GeminiGenerateContentProvider,ProviderError,_observe,benchmark)
from atof.models import OptimizeRequest

PAYLOAD=OptimizeRequest(task='Analyze database error',
  error_output='heartbeat ok\n'*140+'RuntimeError: database unavailable\n')

def test_synthetic_run_cannot_claim_provider_savings():
    r=benchmark(PAYLOAD,SyntheticProvider(),required_terms=('Synthetic reply',))
    assert r['status']=='completed' and r['provider_calls']==2
    assert r['provider_usage_measured'] is False
    assert r['provider_savings_verified'] is False
    assert r['input_token_difference'] is None
    assert r['baseline']['input_tokens']>r['optimized']['input_tokens']

def test_reverse_order_same_synthetic_counts():
    a=benchmark(PAYLOAD,SyntheticProvider(),order='AB')
    b=benchmark(PAYLOAD,SyntheticProvider(),order='BA')
    assert a['baseline']['input_tokens']==b['baseline']['input_tokens']

def test_nonreducing_fixture_makes_no_provider_calls():
    r=benchmark(OptimizeRequest(task='Analyze error',error_output='RuntimeError: x'),SyntheticProvider())
    assert r['provider_calls']==0

def test_agent_requests_not_benchmarked_as_controlled_api():
    with pytest.raises(ValueError):
        benchmark(PAYLOAD.model_copy(update={'agent':'copilot'}),SyntheticProvider())

def test_openai_usage_parsed_without_network(monkeypatch):
    from atof import benchmark as bm
    monkeypatch.setattr(bm,'_post_json',lambda *args,**kwargs:{
      'status':'completed','usage':{'input_tokens':55,'output_tokens':12,'input_tokens_details':{'cached_tokens':20}},
      'output':[{'type':'message','content':[{'type':'output_text','text':'Success'}]}]})
    r=OpenAIResponsesProvider('test',api_key='mock').generate('prompt',('Success',))
    assert (r.input_tokens,r.output_tokens,r.cached_input_tokens)==(55,12,20)

def test_gemini_usage_parsed_without_network(monkeypatch):
    from atof import benchmark as bm
    monkeypatch.setattr(bm,'_post_json',lambda *args,**kwargs:{
      'usageMetadata':{'promptTokenCount':80,'candidatesTokenCount':19,'cachedContentTokenCount':10},
      'candidates':[{'content':{'parts':[{'text':'database unavailable'}]}}]})
    r=GeminiGenerateContentProvider('test',api_key='mock').generate('prompt',('database',))
    assert (r.input_tokens,r.output_tokens,r.cached_input_tokens)==(80,19,10)

def test_missing_or_invalid_provider_usage_is_rejected():
    with pytest.raises(ProviderError):_observe('',(),None,0,None,0,'real')
    with pytest.raises(ProviderError):_observe('',(),10,0,12,0,'real')

def test_missing_key_prevents_live_call(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    with pytest.raises(ProviderError):OpenAIResponsesProvider('test')

def test_invalid_gemini_model_path_is_rejected():
    with pytest.raises(ValueError):
        GeminiGenerateContentProvider('../../secret',api_key='mock')

def test_lexical_gate_cannot_claim_semantic_equivalence():
    r=benchmark(PAYLOAD,SyntheticProvider(),required_terms=('Synthetic reply',))
    assert r['quality_gate_passed']
    assert r['task_quality_gate'].startswith('required_terms_only')
