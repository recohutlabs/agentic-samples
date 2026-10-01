"""Compare production extraction and verification on frozen PDF expectations."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse,json,hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from time import monotonic
from agents.classifier import classify
from agents.extractor import extract_candidate
from agents.verifier import verify_contract
from config import load_openai_config
from registry import CONTRACT_TYPES
from tools.pdf_reader import read_contract_text
from evaluation.grading import grade

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def run_case(case,key,model,output):
    """Keep both outputs and failures. Expected answers never enter the model context."""
    r={'id':case['id'],'pdf':case['pdf'],'pdf_sha256':digest(ROOT/case['pdf']),'expected_type':case['contract_type'],'stage_seconds':{}}
    stage='read'
    try:
        text=read_contract_text(ROOT/case['pdf'])
        stage='classification';start=monotonic();kind=classify(text,key,model,CONTRACT_TYPES)
        r['stage_seconds'][stage]=round(monotonic()-start,2)
        r['actual_type']=kind;r['classification_passed']=kind==case['contract_type']
        if kind not in CONTRACT_TYPES or not r['classification_passed']:
            r['error']='Classification mismatch; extraction not attempted';return r
        definition=CONTRACT_TYPES[kind]
        stage='extraction';start=monotonic();candidate=extract_candidate(text,kind,definition,key,model)
        r['stage_seconds'][stage]=round(monotonic()-start,2)
        raw=candidate.model_dump(mode='json')
        (output/f"{case['id']}.extracted.json").write_text(json.dumps(raw,indent=2)+'\n')
        r['extraction_checks']=grade(raw,case['checks'])
        stage='verification';start=monotonic();verified=verify_contract(text,candidate,kind,definition,key,model)
        r['stage_seconds'][stage]=round(monotonic()-start,2)
        final=verified.model_dump(mode='json')
        (output/f"{case['id']}.verified.json").write_text(json.dumps(final,indent=2)+'\n')
        r['verification_checks']=grade(final,case['checks'])
        pairs=list(zip(r['extraction_checks'],r['verification_checks']))
        r['improved']=[b['path'] for a,b in pairs if not a['passed'] and b['passed']]
        r['regressed']=[b['path'] for a,b in pairs if a['passed'] and not b['passed']]
        r['remaining_failures']=[b['path'] for b in r['verification_checks'] if not b['passed']]
    except Exception as error:r['error']=f'{stage} failed ({type(error).__name__})'
    finally:
        (output/f"{case['id']}.result.json").write_text(json.dumps(r,indent=2)+'\n')
        print(f"{case['id']}: {r.get('error',str(len(r.get('remaining_failures',[])))+' final mismatches')}",file=sys.stderr,flush=True)
    return r

def main():
    """Run one live trial per fixture with two bounded concurrent cases."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'evaluation/runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    expected=ROOT/'evaluation/expected.json';suite=json.loads(expected.read_text());key,model=load_openai_config()
    files=[p for folder in ['agents','prompts','models'] for p in (ROOT/folder).glob('*.py')]+[ROOT/'registry.py',ROOT/'config.py',ROOT/'workflow.py',ROOT/'tools/pdf_reader.py',Path(__file__),ROOT/'evaluation/grading.py']
    manifest={'model':model,'run_utc':datetime.now(timezone.utc).isoformat(),'suite_sha256':digest(expected),'repetitions':1,'source_hashes':{str(p.relative_to(ROOT)):digest(p) for p in files}}
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (args.output/'expected.json').write_text(expected.read_text())
    print(f"Starting {len(suite['cases'])} cases: {args.output}",file=sys.stderr,flush=True)
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda c:run_case(c,key,model,args.output),suite['cases']))
    total=sum(len(c['checks']) for c in suite['cases'])
    before=sum(sum(c['passed'] for c in r.get('extraction_checks',[])) for r in results)
    after=sum(sum(c['passed'] for c in r.get('verification_checks',[])) for r in results)
    errors=sum('error' in r for r in results)
    report={'manifest':manifest,'contracts':len(results),'classification_passed':sum(r.get('classification_passed',False) for r in results),'checks_per_stage':total,'extraction_passed':before,'verification_passed':after,'improved':sum(len(r.get('improved',[])) for r in results),'regressed':sum(len(r.get('regressed',[])) for r in results),'errors':errors,'cases':results,'decision':'hold' if errors or after<total else 'pass_focused_suite'}
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('manifest','cases')},indent=2))
    return 1 if errors or after<total else 0
if __name__=='__main__':raise SystemExit(main())
