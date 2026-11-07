"""Actual HTTP smoke checks against the local running app, without generation calls."""
import json
from datetime import datetime, timezone
import requests
from config import DATA

def main():
    base='http://127.0.0.1:8000'
    session=requests.Session()
    before=session.get(base+'/api/status',timeout=10).json()
    cases=[
        ('attendance retrieval', {'question':'ما الحد الأدنى لنسبة الحضور؟','mode':'retrieve'},'retrieved','retrieval_only'),
        ('course credits', {'question':'كم ساعة البرمجة المتقدمة؟'},'answered','deterministic'),
        ('GPA row', {'question':'معدلي 2.1 وأنا سنة ثالثة، كم ساعة بقدر أسجل؟'},'partially_answered','deterministic'),
        ('GPA followup', {'question':'وإذا صار معدلي 2.8؟','history':['معدلي 2.1 وأنا سنة ثالثة، كم ساعة بقدر أسجل؟']},'partially_answered','deterministic'),
        ('unsupported schedule', {'question':'متى امتحان الخوارزميات الأسبوع القادم؟'},'insufficient_evidence','guardrail'),
        ('out of scope', {'question':'اكتب لي قصيدة عن الجامعة'},'out_of_scope','guardrail'),
    ]
    results=[]
    for name,body,status,origin in cases:
        r=session.post(base+'/api/chat',json={**body},timeout=25)
        r.raise_for_status();data=r.json()
        ok=data['status']==status and data['origin']==origin
        for c in data['citations']:
            source=session.get(base+c['url'],timeout=10)
            ok=ok and source.status_code==200
        results.append({'case':name,'passed':ok,'status':data['status'],'origin':data['origin']})
    after=session.get(base+'/api/status',timeout=10).json()
    report={'created_at':datetime.now(timezone.utc).isoformat(),'cases':results,
        'passed':sum(x['passed'] for x in results),'total':len(results),
        'zero_gemini_calls':after['api_attempts_today_utc']==before['api_attempts_today_utc'],
        'genuine_documents':after['genuine_documents'],'model':after['gemini'],'semantic_enabled':after['semantic_enabled']}
    (DATA/'smoke_results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True,indent=2))
    return 0 if report['passed']==report['total'] and report['zero_gemini_calls'] else 1

if __name__=='__main__':raise SystemExit(main())
