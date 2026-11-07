"""Offline retrieval/behavior evaluation. Never claims human or LLM-grounding review."""
import copy
import json
from datetime import datetime, timezone
from config import DATA, ROOT
from rag import store
from rag.retrieval import retriever
from rag.service import answer

def run():
    from academic.structured import plans
    if plans():
        from evaluation.hebron import run as run_hebron
        return run_hebron()
    definition = json.loads((ROOT / 'evaluation' / 'cases.json').read_text(encoding='utf-8'))
    rows = {r['id']: r for r in retriever.rows}
    if not any(r['document_id']=='demo-regs' for r in rows.values()):
        return {'status':'demo_documents_missing','cases':[], 'message':'Load fictional test documents with python -m scripts.seed_demo, or replace cases with reviewed genuine-document references.'}
    results = []
    for case in definition['cases']:
        q = case['question']
        from academic.rules import resolve_question
        resolved, _ = resolve_question(q, case.get('history', []))
        retrieved = retriever.search(resolved, limit=5, corpus='synthetic', program='DEMO-CS')
        found = {r['id'] for r in retrieved}
        relevant = set(case['evidence_ids'])
        scoreable = bool(relevant) and relevant <= rows.keys()
        hit = int(bool(found & relevant)) if scoreable else None
        precision = len(found & relevant) / 5 if scoreable else None
        if case.get('fixture') == 'conflict':
            # Isolated domain fixture: never mutate the shared retriever or persistent KB.
            from academic.rules import evaluate_course
            duplicate = copy.deepcopy(next(r for r in retriever.rows if r.get('course',{}).get('code')=='CS102'))
            duplicate['id'] = 'test-only-conflict'
            duplicate['version'] = 'DEMO-2025'
            domain = evaluate_course(q, retriever.rows + [duplicate], corpus='synthetic')
            output = {'status':domain['status'], 'answer':domain['answer'], 'citations':[]}
        else:
            output = answer(q, mode=case['mode'], history=case.get('history',[]), corpus='synthetic', program='DEMO-CS', offline=True)
        citation_failures = sum(1 for c in output['citations'] if c['id'] not in rows or
            (c['id'] in rows and (c['excerpt'] != rows[c['id']]['text'] or c['pdf_page'] != rows[c['id']].get('pdf_page'))))
        status_ok = output['status'] == case['expected_status']
        contains_ok = all(s in output['answer'] for s in case.get('contains', []))
        # Multi-source cases require all their listed evidence within the retrieval budget.
        retrieval_ok = relevant <= found if case['id']=='multi' else (bool(hit) if scoreable else True)
        passed = status_ok and contains_ok and retrieval_ok and citation_failures==0
        results.append({**case, 'retrieved_ids':[r['id'] for r in retrieved], 'actual_status':output['status'],
                        'actual_answer':output['answer'], 'hit_at_5':hit, 'precision_at_5':precision,
                        'citation_failures':citation_failures, 'passed':passed,
                        'human_verified':definition['human_verified']})
    measured = [r for r in results if r['hit_at_5'] is not None]
    report = {'status':'completed', 'created_at':datetime.now(timezone.utc).isoformat(),
        'dataset':'Fictional demo corpus only; no university claims', 'reference_review_status':definition['reference_review_status'],
        'human_verified':definition['human_verified'], 'metrics_provisional':not definition['human_verified'],
        'total':len(results), 'passed':sum(r['passed'] for r in results),
        'hit_at_5':sum(r['hit_at_5'] for r in measured)/len(measured) if measured else None,
        'precision_at_5':sum(r['precision_at_5'] for r in measured)/len(measured) if measured else None,
        'citation_failures':sum(r['citation_failures'] for r in results), 'cases':results,
        'generation_grounding_review':'Not measured by this offline suite; human claim review required',
        'semantic_enabled':retriever.vectors is not None}
    (DATA / 'evaluation_results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    lines = ['# Actual local evaluation', '', f"Run: {report['created_at']}", '', report['dataset'], '',
        report['reference_review_status'], '', f"Passed: {report['passed']}/{report['total']}",
        f"Provisional Hit@5: {report['hit_at_5']}; Precision@5: {report['precision_at_5']}",
        f"Citation location failures: {report['citation_failures']}", '',
        'Precision uses a fixed denominator of 5. References are incomplete drafts, so metrics require human review.',
        'Generation claim grounding is NOT measured by this offline run.', '',
        '| Case | Status | Hit@5 | Precision@5 | Passed |', '|---|---|---|---|---|']
    lines.extend(f"| {r['id']} | {r['actual_status']} | {r['hit_at_5']} | {r['precision_at_5']} | {r['passed']} |" for r in results)
    (DATA / 'evaluation_results.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return report

if __name__ == '__main__':
    store.init()
    retriever.refresh()
    result = run()
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},indent=2))
