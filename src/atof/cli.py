import json
from pathlib import Path
from .models import OptimizeRequest
from .service import optimize

def main():
    import argparse
    parser=argparse.ArgumentParser(description='ATOF Phase 1 demo')
    parser.add_argument('--file',default='examples/sample_request.json')
    args=parser.parse_args()
    request=OptimizeRequest.model_validate_json(Path(args.file).read_text(encoding='utf-8'))
    print(json.dumps(optimize(request).model_dump(),indent=2))
if __name__=='__main__':main()
