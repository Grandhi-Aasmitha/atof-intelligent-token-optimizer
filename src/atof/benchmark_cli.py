"""Explicit two-arm benchmark CLI. Real provider calls require consent."""
import argparse, json
from pathlib import Path
from .models import OptimizeRequest
from .benchmark import (benchmark,SyntheticProvider,OpenAIResponsesProvider,
                        GeminiGenerateContentProvider,ProviderError)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--provider',choices=('synthetic','openai','gemini'),default='synthetic')
    p.add_argument('--model',default='')
    p.add_argument('--fixture',type=Path)
    p.add_argument('--order',choices=('AB','BA'),default='AB')
    p.add_argument('--require-term',action='append',default=[])
    p.add_argument('--accept-paid-calls',action='store_true')
    args=p.parse_args()
    if args.provider!='synthetic' and not args.accept_paid_calls:
        p.error('Add --accept-paid-calls for two provider requests that may incur charges')
    if args.provider!='synthetic' and not args.model: p.error('Specify --model')
    if args.fixture:
        data=json.loads(args.fixture.read_text(encoding='utf-8'))
    else:
        data={'task':'Analyze root cause of RuntimeError',
              'error_output':'heartbeat ok\n'*150+'RuntimeError: database unavailable\n'}
    request=OptimizeRequest.model_validate(data)
    try:
        provider={'synthetic':lambda:SyntheticProvider(),
                  'openai':lambda:OpenAIResponsesProvider(args.model),
                  'gemini':lambda:GeminiGenerateContentProvider(args.model)}[args.provider]()
        print(json.dumps(benchmark(request,provider,required_terms=tuple(args.require_term),order=args.order),indent=2))
    except (ProviderError,ValueError) as ex:
        p.exit(2,'Benchmark failed: '+str(ex)+'\n')
if __name__=='__main__':main()
