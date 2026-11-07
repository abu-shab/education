"""Actual HTTP acceptance checks and source-byte checks; no generation request."""
import hashlib
import json
from datetime import datetime,timezone
import requests
from config import DATA,ROOT

def main():
    base='http://127.0.0.1:8000';s=requests.Session()
    before=s.get(base+'/api/status',timeout=20).json()
    definition=json.loads((ROOT/'evaluation'/'hebron_cases.json').read_text(encoding='utf-8'))
    results=[]
    for case in definition['cases']:
        body={'question':case['question'],'mode':case.get('mode','generate'),'corpus':'real',
              **{k:case[k] for k in ('plan_id','knowledge_scope') if k in case}}
        response=s.post(base+'/api/chat',json=body,timeout=30);response.raise_for_status();actual=response.json()
        passed=actual['status']==case['expected_status'] and all(x in actual['answer'] for x in case.get('contains',[]))
        for c in actual['citations']:
            page=s.get(base+c['url'],timeout=15)
            passed=passed and page.status_code==200
        results.append({'id':case['id'],'passed':passed,'status':actual['status'],'origin':actual['origin'],
                        'evidence_ids':[c['id'] for c in actual['citations']]})
    manifest=s.get(base+'/api/source-manifest',timeout=10).json();files=[]
    for source in manifest['files']:
        r=s.get(base+'/api/documents/'+source['document_id']+'/file',timeout=20)
        files.append({'filename':source['filename'],'passed':r.status_code==200 and hashlib.sha256(r.content).hexdigest()==source['sha256']})
    after=s.get(base+'/api/status',timeout=10).json()
    report={'created_at':datetime.now(timezone.utc).isoformat(),'passed':sum(r['passed'] for r in results),'total':len(results),
        'original_pdf_routes_passed':sum(r['passed'] for r in files),'original_pdf_routes_total':len(files),
        'zero_gemini_calls':before['api_attempts_today_utc']==after['api_attempts_today_utc'],
        'semantic_enabled':after['semantic_enabled'],'gemini':after['gemini'],'cases':results,'original_files':files}
    (DATA/'hebron_http_results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('cases','original_files')},indent=2))
    return 0 if report['passed']==report['total'] and report['original_pdf_routes_passed']==len(files) and report['zero_gemini_calls'] else 1

if __name__=='__main__':raise SystemExit(main())
