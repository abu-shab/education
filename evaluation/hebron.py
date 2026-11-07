import json
from datetime import datetime,timezone
from config import DATA,ROOT
from rag import store
from rag.retrieval import retriever
from rag.service import answer
from academic.structured import course_records

def run():
    definition=json.loads((ROOT/'evaluation'/'hebron_cases.json').read_text(encoding='utf-8'))
    stored={r['id']:r for r in retriever.rows}
    rows=course_records();results=[]
    for case in definition['cases']:
        kwargs={k:case[k] for k in ('plan_id','knowledge_scope') if k in case}
        output=answer(case['question'],mode=case.get('mode','generate'),corpus='real',offline=True,**kwargs)
        evidence_ids=[]
        if case.get('document_id'):
            evidence_ids=[r['id'] for r in stored.values() if r['document_id']==case['document_id'] and r['pdf_page']==case['page']
                and (case.get('code','').upper() in r.get('course_codes',[]) if case.get('code') else True)]
        retrieved=retriever.search(case['question'],limit=5,corpus='real',scope=case.get('scope','academic'),plan_id=case.get('plan_id'))
        found={r['id'] for r in retrieved};relevant=set(evidence_ids)
        hit=int(bool(found&relevant)) if relevant else None
        precision=len(found&relevant)/5 if relevant else None
        citation_failures=sum(c['id'] not in stored or c['pdf_page']!=stored[c['id']]['pdf_page'] or
            c['excerpt']!=stored[c['id']]['text'] for c in output['citations'])
        correct_doc=not case.get('document_id') or (any(c['document_id']==case['document_id'] and c['pdf_page']==case['page'] for c in output['citations']))
        isolation=all(c['document_id']=='hu-conduct' for c in output['citations']) if case['id']=='conduct-isolation' else True
        passed=output['status']==case['expected_status'] and all(x in output['answer'] for x in case.get('contains',[])) and not citation_failures and correct_doc and isolation
        results.append({**case,'evidence_ids':evidence_ids,'retrieved_ids':[r['id'] for r in retrieved],
            'actual_status':output['status'],'actual_answer':output['answer'],'origin':output['origin'],
            'hit_at_5':hit,'precision_at_5':precision,'citation_failures':citation_failures,'passed':passed,
            'reviewed':True,'review_method':'AI visual source review; not human sign-off'})
    measured=[r for r in results if r['hit_at_5'] is not None]
    with store.connect() as db:
        excluded_leaks=db.execute("SELECT count(*) FROM chunks c JOIN documents d ON d.id=c.document_id WHERE d.inclusion_status='excluded'").fetchone()[0]
        foreign_key_errors=[tuple(r) for r in db.execute('PRAGMA foreign_key_check')]
    report={'status':'completed','created_at':datetime.now(timezone.utc).isoformat(),'dataset':'Supplied Hebron University PDFs',
        'reference_review_status':definition['review_method'],'human_verified':False,'metrics_provisional':True,
        'total':len(results),'passed':sum(r['passed'] for r in results),
        'hit_at_5':sum(r['hit_at_5'] for r in measured)/len(measured) if measured else None,
        'precision_at_5':sum(r['precision_at_5'] for r in measured)/len(measured) if measured else None,
        'citation_failures':sum(r['citation_failures'] for r in results),'semantic_enabled':retriever.vectors is not None,
        'excluded_document_chunk_leaks':excluded_leaks,'foreign_key_errors':foreign_key_errors,
        'verified_course_records':sum(r['review_status']=='visual_checked_core_fields' for r in rows),
        'unverified_course_records':sum(r['review_status']!='visual_checked_core_fields' for r in rows),
        'generation_grounding_review':'This runner makes no Gemini calls; live generation reviewed separately.','cases':results}
    for name in ('evaluation_results.json','hebron_evaluation_results.json'):
        (DATA/name).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Actual Hebron source evaluation','',report['created_at'],'',definition['review_method'],'',
           f"Passed: {report['passed']}/{report['total']}; provisional Hit@5 {report['hit_at_5']}; Precision@5 {report['precision_at_5']}",'',
           '| Case | Observed status | Pass |','|---|---|---|']
    lines.extend(f"| {r['id']} | {r['actual_status']} | {r['passed']} |" for r in results)
    text='\n'.join(lines)+'\n'
    (DATA/'evaluation_results.md').write_text(text,encoding='utf-8')
    (ROOT/'docs'/'HEBRON_EVALUATION_RESULTS.md').write_text(text,encoding='utf-8')
    return report
