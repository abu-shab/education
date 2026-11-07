"""Idempotent, source-linked import into the existing app, never a replacement DB."""
import hashlib
import json
import re
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import pymupdf
from config import DATA, ROOT
from rag import store
from rag.text import normalize, codes
from rag.ingestion import section_chunks
from academic.pdf_tables import extract_course_rows, compact
from academic.hebron_catalog import PLANS, FORMS, EXCLUSIONS, EXCLUDED_METADATA

def dumps(value):return json.dumps(value,ensure_ascii=False)

def cell_rule(expression):
    if expression is None:return 'unknown',[]
    if re.fullmatch(r'[-–—\s]+',expression):return 'explicit_none',[]
    values=codes(expression)
    if len(values)==1 and normalize(expression).upper()==values[0]:return 'single_passed_course',values
    return 'notation_unverified',values

def requirement_heading(page, top, previous):
    choices=[]
    for b in page.get_text('blocks'):
        text=compact(b[4]);n=normalize(text)
        if b[1] < top and 'متطلبات' in n and not 'رقم المساق' in n and not codes(text):
            choices.append((b[1],text))
    heading=max(choices)[1] if choices else previous
    n=normalize(heading or '')
    # Some PDFs encode the lam-alef ligature as اال / اإل. Match the
    # distinctive suffix, while preserving the original heading unchanged.
    mandatory=0 if 'ختياري' in n else (1 if 'جباري' in n else None)
    return heading,mandatory

def backup_database():
    path=DATA/'academia.sqlite'
    if path.exists():
        folder=DATA/'backups';folder.mkdir(exist_ok=True)
        target=folder/('before_hebron_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.sqlite')
        with sqlite3.connect(path) as source,sqlite3.connect(target) as dest:source.backup(dest)

def source_hashes():
    """A review cannot silently follow changed bytes at the same filename."""
    path=ROOT/'academic'/'hebron_review_hashes.json'
    if path.exists():return json.loads(path.read_text(encoding='utf-8'))
    return {'reviewer':None,'human_signoff':False,'sha256':{}}

def main():
    backup_database();store.init();review=source_hashes()
    incoming=DATA/'incoming'; originals=DATA/'originals';originals.mkdir(exist_ok=True)
    (DATA/'inspection').mkdir(exist_ok=True)
    by_filename={p['filename']:p for p in PLANS}
    manifest=[];failures=[]
    for path in sorted(incoming.glob('*.pdf')):
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        untouched=originals/path.name
        if untouched.exists() and hashlib.sha256(untouched.read_bytes()).hexdigest()!=digest:
            untouched=originals/(digest[:12]+'_'+path.name)
        if not untouched.exists():shutil.copy2(path,untouched)
        filename=path.name;plan=by_filename.get(filename)
        number=filename[:3] if re.match(r'^\d{3}-form.pdf$',filename) else None
        excluded=filename in EXCLUSIONS
        kind='plan' if plan else ('form' if number in FORMS else ('conduct' if filename=='conduct.pdf' else 'excluded'))
        included=kind!='excluded' and not excluded
        reviewed=review['sha256'].get(filename)==digest
        title=(plan['name_ar']+' — '+str(plan['year'])) if plan else (FORMS[number][0] if number in FORMS else
            ('مدونة قواعد سلوك أعضاء الهيئة التدريسية والطلبة في جامعة الخليل' if kind=='conduct' else path.stem))
        document_type=EXCLUDED_METADATA[filename][0] if filename in EXCLUDED_METADATA else kind
        if filename in EXCLUDED_METADATA:title=EXCLUDED_METADATA[filename][1]
        document_id=plan['id'] if plan else ('hu-form-'+number if number in FORMS else ('hu-conduct' if kind=='conduct' else 'hu-excluded-'+digest[:12]))
        stored_name=document_id+'.pdf';shutil.copy2(path,DATA/'uploads'/stored_name)
        entry={'filename':filename,'document_id':document_id,'document_type':document_type,'title':title,
               'program':plan['name_ar'] if plan else None,'plan_year':plan['year'] if plan else None,
               'document_version':str(plan['year']) if plan else None,'sha256':digest,'source_url':None,
               'source_institution':'Hebron University (user-supplied; hebron.edu)',
               'pdf_page_count':None,'inclusion_status':'included' if included else 'excluded',
               'review_status':'representative_visual_review' if reviewed and included else 'unreviewed',
               'exclusion_reason':EXCLUSIONS.get(filename,'Unclassified source' if not included else None),
               'extraction_result':'not_started','verified_course_records':0,'unverified_course_records':0,
               'indexed_pages':0,'indexed_chunks':0,'warnings':list(plan.get('warnings',[])) if plan else []}
        try:
            with pymupdf.open(path) as pdf:
                entry['pdf_page_count']=len(pdf)
                pages=[{'page':i+1,'pdf_page':i+1,'printed_page':p.get_label() or None,'text':p.get_text(),'tables':[]} for i,p in enumerate(pdf)]
                if not any(p['text'].strip() for p in pages):raise ValueError('No extractable text; OCR/review required')
                with store.connect() as db:
                    # Delete only this importer-owned document. Originals and teammate files remain untouched.
                    db.execute('DELETE FROM documents WHERE id=?',(document_id,))
                    db.execute('''INSERT INTO documents(id,title,filename,version,program,synthetic,status,sha256,kind,
                        original_filename,document_type,plan_year,source_url,pdf_page_count,inclusion_status,review_status,exclusion_reason)
                        VALUES(?,?,?,?,?,0,?,?,?,?,?,?,?,?,?,?,?)''',
                        (document_id,title,stored_name,str(plan['year']) if plan else '',plan['name_ar'] if plan else 'جامعة الخليل',
                         'ready' if included else 'excluded',digest,kind,filename,document_type,plan['year'] if plan else None,None,len(pdf),
                         entry['inclusion_status'],entry['review_status'],entry['exclusion_reason']))
                    if not included:
                        entry['extraction_result']='inspected_not_indexed';manifest.append(entry);continue
                    chunks=[];refs=[]
                    for p in pages:
                        if not p['text'].strip():continue
                        entry['indexed_pages']+=1
                        # Preserve original page text as well as smaller source-linked passages.
                        for i,text in enumerate(section_chunks(p['text'])):
                            # Intact numbered articles preserve their conditions. Ordinary pages are
                            # also searchable through short table-row chunks below.
                            chunk_id=f'{document_id}-p{p["page"]}-text{i}'
                            meta={'page':p['page'],'pdf_page':p['page'],'printed_page':p['printed_page'],
                                  'article':None,'course_codes':codes(text),'academic_plan_id':plan['id'] if plan else None,
                                  'evidence_type':'page_text','review_status':'extracted_unverified'}
                            chunks.append((chunk_id,document_id,text,normalize(text),dumps(meta)))
                        reference=f'{document_id}:page:{p["page"]}'
                        refs.append((reference,document_id,p['page'],None,p['text'],f'{document_id}-p{p["page"]}-text0',
                                     'visual_checked_title' if reviewed and p['page']==1 else 'extracted_unverified',
                                     'Rendered PDF inspection' if reviewed and p['page']==1 else None,
                                     'Codex AI' if reviewed and p['page']==1 else None))
                    db.executemany('INSERT INTO chunks VALUES(?,?,?,?,?)',chunks)
                    db.executemany('INSERT INTO source_references VALUES(?,?,?,?,?,?,?,?,?)',refs)
                    if plan:
                        db.execute('INSERT INTO programs VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET name_ar=excluded.name_ar,name_en=excluded.name_en',
                                   (plan['program_id'],plan['name_ar'],plan['name_en'],'Hebron University'))
                        first=pages[0]['text']
                        # These exact totals/years were read visually and are bound to
                        # the reviewed bytes. Some PDFs split 138 into glyph spans 8/13,
                        # or 2022 into 22/20, so raw text search cannot validate them.
                        total_ok=reviewed
                        db.execute('INSERT INTO study_plans VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                            (plan['id'],plan['program_id'],document_id,title,plan['year'],str(plan['year']),
                             plan['total_credits'] if total_ok else None,document_id+':page:1',
                             'visual_checked_title_year_total' if total_ok else 'unverified','all_pages_extracted_rows_pending_review',dumps(entry['warnings'])))
                        previous_heading=None;all_rows=[]
                        for i,page in enumerate(pdf):
                            rows,issues=extract_course_rows(page)
                            for issue_index,issue in enumerate(issues):
                                db.execute('INSERT INTO review_queue VALUES(?,?,?,?,?,?,?,?)',
                                    (f'{document_id}:geometry:{i}:{issue_index}',document_id,None,f'{document_id}:page:{i+1}',issue['reason'],dumps(issue),'pending',None))
                            for j,row in enumerate(rows):
                                heading,mandatory=requirement_heading(page,row['bbox'][1],previous_heading)
                                previous_heading=heading
                                row.update({'pdf_page':i+1,'requirement_category':heading,'mandatory':mandatory})
                                observed=next((r for r in plan['reviewed_rows'] if r[0]==i+1 and r[1]==row['code']),None) if reviewed else None
                                fields=[];status='unverified'
                                if observed:
                                    # No repair from a neighboring plan: every reviewed value must match this row.
                                    same_hours=row['credit_hours']==observed[2]
                                    actual_expr=row['prerequisite_expression']
                                    same_expr=(observed[3]=='-' and actual_expr is not None and re.fullmatch(r'[-\s]+',actual_expr)) or \
                                        (actual_expr is not None and normalize(actual_expr)==normalize(observed[3]))
                                    if same_hours and same_expr:
                                        status='visual_checked_core_fields';fields=['code','credit_hours','prerequisite_expression']
                                course_id=plan['id']+':'+row['code'].upper()
                                pc_id=f'{plan["id"]}:p{i+1}:r{j}'
                                ref_id=pc_id+':ref';chunk_id=pc_id.replace(':','-')
                                excerpt='Course Name | متطلب سابق | ساعة معتمدة | اسم المساق | رقم المساق\n'+ \
                                    ' | '.join([row['name_en'],row['prerequisite_expression'] or '[blank / unknown]',str(row['credit_hours']) if row['credit_hours'] is not None else '[unknown]',row['name_ar'],row['code']])
                                meta={'page':i+1,'pdf_page':i+1,'printed_page':page.get_label() or None,'article':None,
                                      'course_codes':codes(excerpt),'academic_plan_id':plan['id'],
                                      'evidence_type':'course_row','review_status':status,'verified_fields':fields,
                                      'requirement_category':heading,'mandatory':mandatory,'bbox':row['bbox']}
                                db.execute('INSERT INTO chunks VALUES(?,?,?,?,?)',(chunk_id,document_id,excerpt,normalize(excerpt),dumps(meta)))
                                db.execute('INSERT INTO source_references VALUES(?,?,?,?,?,?,?,?,?)',
                                    (ref_id,document_id,i+1,dumps(row['bbox']),excerpt,chunk_id,status,
                                     'Compared code, hours and expression with rendered source' if fields else None,'Codex AI' if fields else None))
                                db.execute('INSERT INTO courses VALUES(?,?,?,?,?) ON CONFLICT(id) DO NOTHING',
                                           (course_id,row['code'],row['code'].upper(),row['name_ar'],row['name_en']))
                                db.execute('INSERT INTO plan_courses VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                                    (pc_id,plan['id'],course_id,row['credit_hours'],heading,mandatory,row['prerequisite_expression'],ref_id,status,dumps(fields),dumps(row)))
                                interpretation,required_codes=cell_rule(row['prerequisite_expression'])
                                rule_status='visual_checked' if fields and interpretation in ('single_passed_course','explicit_none') else 'unverified'
                                db.execute('INSERT INTO prerequisite_rules VALUES(?,?,?,?,?,?,?)',
                                    (pc_id+':rule',pc_id,row['prerequisite_expression'],interpretation,dumps(required_codes),rule_status,ref_id))
                                reasons=list(row['validation_issues'])
                                if not fields:reasons.append('Core fields have not been visually compared with the PDF')
                                if not heading or mandatory is None:reasons.append('Requirement category or mandatory/elective status unresolved')
                                if interpretation in ('unknown','notation_unverified'):reasons.append('Blank prerequisite or undefined source notation; do not assume AND/OR/concurrency')
                                if reasons:
                                    db.execute('INSERT INTO review_queue VALUES(?,?,?,?,?,?,?,?)',
                                        (pc_id+':review',document_id,pc_id,ref_id,'; '.join(reasons),dumps(row),'pending',None))
                                all_rows.append(row)
                                entry['verified_course_records' if fields else 'unverified_course_records']+=1
                        (DATA/'inspection'/(path.stem+'.imported_rows.json')).write_text(dumps(all_rows),encoding='utf-8')
                        for n,warning in enumerate(entry['warnings']):
                            db.execute('INSERT INTO review_queue VALUES(?,?,?,?,?,?,?,?)',
                                (document_id+':warning:'+str(n),document_id,None,document_id+':page:1',warning,'{}','pending',None))
                    elif kind=='form':
                        official_title,intended,keywords=FORMS[number]
                        ref_id=document_id+':page:1'
                        db.execute('INSERT INTO academic_forms VALUES(?,?,?,?,?,?,?,?)',
                            (document_id,document_id,number,official_title,intended,keywords,'visual_checked_title_use' if reviewed else 'unverified',ref_id))
                        catalog_text=official_title+'\n'+intended+'\n'+keywords+'\n'+pages[0]['text']
                        catalog_id=document_id+'-catalog'
                        db.execute('INSERT INTO chunks VALUES(?,?,?,?,?)',(catalog_id,document_id,catalog_text,normalize(catalog_text),
                            dumps({'page':1,'pdf_page':1,'printed_page':None,'article':None,'course_codes':[],
                                   'evidence_type':'form_catalog','review_status':'visual_checked_title_use' if reviewed else 'unverified'})))
                        db.execute('UPDATE source_references SET chunk_id=? WHERE id=?',(catalog_id,ref_id))
                    entry['indexed_chunks']=db.execute('SELECT count(*) FROM chunks WHERE document_id=?',(document_id,)).fetchone()[0]
                    entry['extraction_result']='success'
        except Exception as exc:
            entry['extraction_result']='failed: '+type(exc).__name__+': '+str(exc)
            for key in ('verified_course_records','unverified_course_records','indexed_pages','indexed_chunks'):entry[key]=0
            failures.append(filename)
        manifest.append(entry)
    expected={p['filename'] for p in PLANS}|{n+'-form.pdf' for n in FORMS}|set(EXCLUSIONS)|{'conduct.pdf'}
    missing=sorted(expected-{x['filename'] for x in manifest})
    failures.extend(missing)
    payload={'created_at':datetime.now(timezone.utc).isoformat(),'institution':'Hebron University',
             'human_review_completed':False,'review_method':'AI visual comparison of titles, totals and representative rows',
             'current_academic_regulations_available':False,'files':manifest,'failures':failures,'missing_files':missing}
    (DATA/'source_manifest.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'docs'/'HEBRON_SOURCE_MANIFEST.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'files':len(manifest),'failed':failures,'included':sum(x['inclusion_status']=='included' for x in manifest),
        'verified_core_rows':sum(x['verified_course_records'] for x in manifest),'unverified_rows':sum(x['unverified_course_records'] for x in manifest)},ensure_ascii=False))
    return 1 if failures else 0

if __name__=='__main__':raise SystemExit(main())
