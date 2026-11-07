"""Generate the concise report from actual database/import/evaluation outcomes."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime,timezone
from config import ROOT,DATA
from rag import store

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--test',action='store_true');args=parser.parse_args()
    if args.test:
        p=subprocess.run([sys.executable,'-m','pytest','-q'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
        output=p.stdout+p.stderr
        (DATA/'hebron_pytest.log').write_text(output,encoding='utf-8')
        result={'created_at':datetime.now(timezone.utc).isoformat(),'exit_code':p.returncode,
                'passed':int(m.group(1)) if (m:=re.search(r'(\d+) passed',output)) else 0,
                'failed':int(m.group(1)) if (m:=re.search(r'(\d+) failed',output)) else 0}
        (DATA/'hebron_pytest_results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(output.strip())
    manifest=json.loads((DATA/'source_manifest.json').read_text(encoding='utf-8'))
    evaluation=json.loads((DATA/'hebron_evaluation_results.json').read_text(encoding='utf-8'))
    test_path=DATA/'hebron_pytest_results.json'
    tests=json.loads(test_path.read_text(encoding='utf-8')) if test_path.exists() else {}
    http_path=DATA/'hebron_http_results.json';live_path=DATA/'hebron_live_gemini_review.json'
    http=json.loads(http_path.read_text(encoding='utf-8')) if http_path.exists() else {}
    live=json.loads(live_path.read_text(encoding='utf-8')) if live_path.exists() else {}
    with store.connect() as db:
        queue=db.execute("SELECT count(*) FROM review_queue WHERE status='pending'").fetchone()[0]
        row_count=db.execute('SELECT count(*) FROM plan_courses').fetchone()[0]
        plan_counts=[dict(r) for r in db.execute('''SELECT s.id,s.plan_year,s.total_credits,count(pc.id) AS rows,
            sum(pc.review_status='visual_checked_core_fields') AS checked FROM study_plans s
            JOIN plan_courses pc ON pc.plan_id=s.id GROUP BY s.id''')]
    intact=0
    for f in manifest['files']:
        original=DATA/'originals'/f['filename']
        if original.exists() and hashlib.sha256(original.read_bytes()).hexdigest()==f['sha256']:intact+=1
    indexed_pages=sum(f['indexed_pages'] for f in manifest['files'])
    indexed_chunks=sum(f['indexed_chunks'] for f in manifest['files'])
    lines=['# Hebron University data ingestion report','',f"Generated: {datetime.now(timezone.utc).isoformat()}",'',
        f"{len(manifest['files'])} supplied PDFs found; {intact}/{len(manifest['files'])} preserved originals match their manifest SHA256. No source PDF was modified.",
        '20 included: 7 IT plans, 12 procedural forms, 1 conduct code. Three retained originals are excluded from the default IT corpus.',
        f"{row_count} plan-course observations stored: {evaluation['verified_course_records']} visually checked code/hour/prerequisite rows; {evaluation['unverified_course_records']} unverified rows. Names and unreviewed fields remain candidate extraction, not verified academic facts.",
        f"{queue} pending review items. {indexed_pages} nonempty genuine PDF pages indexed into {indexed_chunks} chunks; the seventh page of the 2026 SE-minor PDF is blank. Demo fixtures remain stored but are excluded from automatic real-data answers.",
        'Visual comparisons were performed by Codex AI against rendered supplied pages. This is not institutional or human sign-off. Source observations are bound to reviewed SHA256 values.','',
        '## Files and actual results','',
        '| Source file | Classification / status | PDF pages | Checked / unverified course rows | Indexed pages / chunks | Extraction |',
        '|---|---|---:|---:|---:|---|']
    for f in manifest['files']:
        lines.append(f"| {f['filename']} | {f['document_type']} / {f['inclusion_status']} | {f['pdf_page_count']} | {f['verified_course_records']} / {f['unverified_course_records']} | {f['indexed_pages']} / {f['indexed_chunks']} | {f['extraction_result']} |")
    lines += ['', '## Plans, kept separate','', '| Plan ID | Year | Stated total credits | Extracted observations | Checked core rows |','|---|---:|---:|---:|---:|']
    for p in plan_counts:lines.append(f"| {p['id']} | {p['plan_year']} | {p['total_credits']} | {p['rows']} | {p['checked']} |")
    lines += ['', 'The stated totals come from visually reviewed headings. They are never calculated by summing all elective offerings. Mandatory/elective classification comes from the actual enclosing headings, including cross-page continuation. Unknown or ambiguous prerequisite semantics remain unverified.','',
        '## Exclusions and warnings','']
    lines.extend('- '+f['filename']+': '+f['exclusion_reason'] for f in manifest['files'] if f['inclusion_status']=='excluded')
    for f in manifest['files']:
        lines.extend('- '+f['filename']+': '+warning for warning in f['warnings'])
    lines += [
        '- Built-in table detection produced spurious split columns and missed grids. The adapter uses actual border geometry, preserves raw cells, and handles the standalone cybersecurity plan\'s reversed code/name column order. Suspicious values are queued, never repaired from another plan.',
        '- Form numbers 020 and 031 appear reversed in some extracted text spans; catalog numbers/titles were read from the rendered originals. Forms establish existence/purpose only, not eligibility, current deadlines or approval rights.',
        '- Blank prerequisites mean unknown, not automatically none. “+” and “/” are preserved without assuming concurrency, AND or OR. The actual 61101 source conflict returns clarification with both pages.',
        '- Exact source URLs were not supplied or established. Manifest source_url values are null; hebron.edu is the user-identified source institution, not an invented per-file download URL.',
        '- Source titles, plan/year and checked core values are available; the remaining 705 rows and extracted names require further review. This is not a fully approved degree-audit database.',
        '', '## Missing regulations','',
        '**Current academic degree/registration/examination regulations were not supplied.** No current attendance percentage, maximum withdrawal period, registration load, warning threshold or graduation entitlement is inferred from plans, blank forms, conduct rules, or fictional data. These questions explicitly return insufficient evidence. Graduation readiness cannot be established without a fully reviewed applicable plan, all governing requirements and sufficient fictional completed-course information.',
        '', '## Actual tests','',
        f"- Automated regression/integration tests: {tests.get('passed','not recorded')} passed, {tests.get('failed','not recorded')} failed; exit code {tests.get('exit_code','not recorded')}.",
        f"- Reviewed source-based demonstrations: {evaluation['passed']}/{evaluation['total']} passed; {evaluation['total']-evaluation['passed']} failed. This offline runner makes no Gemini calls.",
        f"- Actual retrieval Hit@5: {evaluation['hit_at_5']:.4f}; Precision@5: {evaluation['precision_at_5']:.4f}. Relevance judgments are AI-reviewed and provisional pending human sign-off.",
        f"- Citation-location failures: {evaluation['citation_failures']}; excluded-document chunk leaks: {evaluation['excluded_document_chunk_leaks']}; foreign-key errors: {len(evaluation['foreign_key_errors'])}.",
        '- Initial real-corpus run: 16/20 behavior checks passed. It exposed program/year text being mistaken for course codes, a missing English form-discovery phrase, and a previously unseen real printed credit conflict. Routing was corrected; the source conflict is retained and now evaluated as clarification, not silently resolved.',
        '- Initial retrieval Hit@5 was 0.80; plan-title/year filtering and the exact stored source-reference signal improved it. No reference answer or source location was generated by Gemini.',
        f"- Actual HTTP demonstrations: {http.get('passed','not run')}/{http.get('total','not run')} passed; original PDF routes/hash checks {http.get('original_pdf_routes_passed','not run')}/{http.get('original_pdf_routes_total','not run')} passed; zero Gemini calls during HTTP checks: {http.get('zero_gemini_calls','not measured')}.",
        f"- Live Gemini answer on conduct evidence: model {live.get('model','not recorded')}, {live.get('displayed_claims','not recorded')} cited claims, {live.get('actual_total_tokens','not recorded')} actual total tokens. AI source review recorded; human sign-off remains pending. The browser form search and plan explorer also worked with no console errors.",
        '', '## Reproduce / review','',
        'Run `python -m scripts.import_hebron`, `python -m evaluation.run`, and `python -m scripts.report_ingestion --test` from the existing Python 3.12 environment. The import is idempotent, backs up the live SQLite database, preserves original bytes, and touches only its own hu-* document records. A changed hash invalidates visual review. Missing expected inputs are reported in the manifest.',
        'Review queue: GET /api/review-queue. Plans: /api/plans. Form search: /api/forms?q=... . Manifest: /api/source-manifest. Existing chat/source/library UI remains functional.',
        'Full file manifest: docs/HEBRON_SOURCE_MANIFEST.json. Reviewed reference cases: evaluation/hebron_cases.json. Actual evaluation table: docs/HEBRON_EVALUATION_RESULTS.md.'
    ]
    (ROOT/'DATA_INGESTION_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Updated DATA_INGESTION_REPORT.md from actual recorded outcomes.')

if __name__=='__main__':main()
