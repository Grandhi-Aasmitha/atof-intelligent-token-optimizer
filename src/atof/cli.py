import json
from pathlib import Path
from .models import OptimizeRequest
from .service import optimize
from .reporting import applied_response

def main():
    import argparse
    parser=argparse.ArgumentParser(description='ATOF Phase 1 demo')
    parser.add_argument('--file',default='examples/sample_request.json')
    parser.add_argument('--diagnostics', action='store_true', help='Show internal planning trace rather than applied-only report')
    args=parser.parse_args()
    request=OptimizeRequest.model_validate_json(Path(args.file).read_text(encoding='utf-8'))
    response = optimize(request)
    if not args.diagnostics:
        response = applied_response(response)
    print(json.dumps(response.model_dump(),indent=2))
if __name__=='__main__':main()
