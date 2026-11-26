"""Actual alexgreensh/token-optimizer benchmark; run independent upstream clone."""
import argparse, importlib.util, json, subprocess, sys, html
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

def summarize(data):
    rows=data.get('results')
    if not isinstance(rows,list) or not rows: raise ValueError('Upstream benchmark provided no fixtures')
    categories=defaultdict(lambda:{'total':0,'passed':0,'failed':0,'before':0,'after':0})
    for row in rows:
        if not isinstance(row,dict):raise ValueError('Invalid fixture')
        state=row.get('status')
        if state=='no_compressor':raise ValueError('Upstream compressor not active: fixture validation only')
        if state not in ('pass','FAIL','compressor_error'):raise ValueError('Unknown fixture status')
        g=categories[str(row.get('category','unknown'))]
        g['total']+=1
        g['passed']+=int(state=='pass')
        g['failed']+=int(state!='pass')
        before,after=row.get('raw_tokens'),row.get('compressed_tokens')
        if isinstance(before,int) and isinstance(after,int):
            g['before']+=before
            g['after']+=after
    before=sum(g['before'] for g in categories.values())
    after=sum(g['after'] for g in categories.values())
    return {'total':len(rows),'passed':sum(g['passed'] for g in categories.values()),
       'failed':sum(g['failed'] for g in categories.values()),
       'before':before,'after':after,'removed':before-after,
       'percent':round(100*(before-after)/before,2) if before else 0,
       'categories':dict(sorted(categories.items()))}

def example(upstream, name='git_status_basic'):
    folder=upstream/'skills/token-optimizer/scripts'
    def module(label,file):
        spec=importlib.util.spec_from_file_location(label,folder/file)
        item=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(item)
        return item
    bench=module('upstream_benchmark_fixture','benchmark.py')
    compressor=module('upstream_bash_compressor','bash_compress.py')
    f=next((f for f in bench.FIXTURES if f['name']==name),None)
    if f is None:raise ValueError('Unknown upstream fixture: '+name)
    sys.path.insert(0,str(folder))
    try: compressed=compressor.compress(f['command'],f['raw_output'])
    finally:sys.path.remove(str(folder))
    original=f['raw_output']
    before=bench.estimate_tokens(original)
    after=bench.estimate_tokens(compressed)
    preserved=all(x in compressed for x in f.get('must_preserve',[]))
    forbidden=any(x in compressed for x in f.get('must_not_contain',[]))
    return {'name':name,'raw':original,'optimized':compressed,'before':before,
        'after':after,'preserved_required':preserved,'passed':preserved and not forbidden and after<before}

def html_report(summary, rows, sample):
    escape=lambda x:html.escape(str(x),quote=True)
    table=''.join('<tr><td>'+escape(key)+'</td><td>'+str(g['passed'])+'/'+str(g['total'])+
       '</td><td>'+str(g['before'])+'</td><td>'+str(g['after'])+'</td></tr>' for key,g in summary['categories'].items())
    failures=''.join('<li>'+escape(r.get('name'))+' — '+escape(r.get('status'))+
       ' (reduction='+escape(r.get('ratio'))+', target='+escape(r.get('min_required'))+')</li>' for r in rows if r.get('status')!='pass')
    return ('<!doctype html><html><head><meta charset="utf-8"><title>Token Optimizer test</title>'
      '<style>body{font:16px system-ui;max-width:1100px;margin:30px auto;padding:15px;background:#f5f7fa}'
      'section{background:white;padding:18px;margin:16px 0;border-radius:12px}table{width:100%;border-collapse:collapse}'
      'td,th{padding:9px;border-bottom:1px solid #ccc;text-align:left}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#eee;padding:12px}'
      '.two{display:grid;grid-template-columns:1fr 1fr;gap:15px}</style></head><body>'
      '<h1>Actual upstream Token Optimizer compression test</h1>'
      '<p>Local bytes/4 token estimates, NOT provider-measured token savings.</p>'
      '<section><h2>Fixture results</h2><p>'+str(summary['passed'])+'/'+str(summary['total'])+' passed; '+str(summary['failed'])+' failed</p>'
      '<p>'+str(summary['before'])+' → '+str(summary['after'])+' estimated tokens; '+str(summary['percent'])+'% aggregate reduction on synthetic fixtures.</p></section>'
      '<section><h2>Categories</h2><table><tr><th>Feature category</th><th>Pass/total</th><th>Original</th><th>Compressed</th></tr>'+table+'</table></section>'
      '<section><h2>Original vs optimized: '+escape(sample['name'])+'</h2>'
      '<p>'+str(sample['before'])+' → '+str(sample['after'])+' estimated tokens; required facts preserved: '+str(sample['preserved_required'])+'</p>'
      '<div class="two"><div><h3>Before</h3><pre>'+escape(sample['raw'])+'</pre></div>'
      '<div><h3>After</h3><pre>'+escape(sample['optimized'])+'</pre></div></div></section>'
      '<section><h2>Failing fixtures</h2><ul>'+failures+'</ul></section></body></html>')

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--upstream',type=Path,default=Path('../token-optimizer'))
    parser.add_argument('--output-dir',type=Path,default=Path('demo-results'))
    parser.add_argument('--fixture',default='git_status_basic')
    parser.add_argument('--html',action='store_true',help='Optional legacy standalone HTML export')
    args=parser.parse_args(argv)
    root=args.upstream.resolve()
    measure=root/'skills/token-optimizer/scripts/measure.py'
    if not measure.is_file():
        print('Missing upstream repo at '+str(root)+'; clone it beside ATOF.',file=sys.stderr)
        return 2
    try:
        proc=subprocess.run([sys.executable,str(measure),'benchmark','--json'],cwd=root,
             capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
        data=json.loads(proc.stdout)
        summary=summarize(data)
        sample=example(root,args.fixture)
    except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as e:
        print('Upstream test failed: '+str(e),file=sys.stderr)
        return 2
    out=args.output_dir.resolve()
    out.mkdir(parents=True,exist_ok=True)
    report={'source':'external_upstream_token_optimizer','upstream':str(root),
      'generated_utc':datetime.now(timezone.utc).isoformat(),'summary':summary,
      'example':sample,'fixtures':data['results'],'provider_tokens_saved':None}
    (out/'token-optimizer-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    if args.html:
        (out/'token-optimizer-verification.html').write_text(html_report(summary,data['results'],sample),encoding='utf-8')
    print('TOKEN OPTIMIZER: ACTUAL UPSTREAM COMPRESSION')
    print(f"Fixtures: {summary['passed']}/{summary['total']} passed, {summary['failed']} failed")
    print(f"Estimated fixture tokens: {summary['before']:,} -> {summary['after']:,}; removed {summary['removed']:,} ({summary['percent']}%)")
    for category,g in summary['categories'].items():
        print(f"  {category:22} {g['passed']:2}/{g['total']:<2}  {g['before']:>6} -> {g['after']:<6}")
    print(f"\nACTUAL BEFORE/AFTER ({sample['name']}): {sample['before']} -> {sample['after']} | preserved={sample['preserved_required']}")
    print('--- BEFORE ---\n'+sample['raw']+'\n--- AFTER ---\n'+sample['optimized'])
    for row in data['results']:
        if row.get('status')!='pass':
            print('FAIL: '+row.get('name','unknown')+f" ratio={row.get('ratio')} required={row.get('min_required')}")
    print('Import JSON into the unified ATOF dashboard: '+str(out/'token-optimizer-verification.json'))
    if args.html:
        print('Optional HTML export: '+str(out/'token-optimizer-verification.html'))
    print('Provider tokens saved: UNVERIFIED. No model requests made.')
    return 0 if proc.returncode==0 and not summary['failed'] and sample['passed'] else 1

if __name__=='__main__':sys.exit(main())
