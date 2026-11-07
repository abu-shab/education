"""Source adapter tests plus read-only snapshots of the supplied public corpus."""
import copy
import json
import sqlite3
from pathlib import Path
import pytest
from config import DATA,ROOT
from rag import store
from rag.retrieval import retriever
from rag.service import answer
from rag.text import codes
from academic.structured import plans,course_records
from scripts.import_hebron import cell_rule

@pytest.fixture
def hebron_snapshot(tmp_path,monkeypatch):
    path=DATA/'academia.sqlite'
    if not path.exists():pytest.skip('Supplied Hebron corpus not installed on this machine')
    with sqlite3.connect(path) as source:
        if not source.execute("SELECT 1 FROM sqlite_master WHERE name='study_plans'").fetchone():pytest.skip('No Hebron plans')
        if source.execute('SELECT count(*) FROM study_plans').fetchone()[0]!=7:pytest.skip('Seven supplied plans not yet imported')
        with sqlite3.connect(tmp_path/'academia.sqlite') as target:source.backup(target)
    saved=dict(retriever.__dict__)
    monkeypatch.setattr(store,'DATA',tmp_path)
    retriever.refresh()
    yield
    retriever.__dict__.clear();retriever.__dict__.update(saved)

@pytest.mark.parametrize('text,expected',[
    ('10100',['10100']),('T 1315',['T1315']),('22Tu1',['22TU1']),('221S1',['221S1']),
    ('2022 135 138',[]),('Computer Science 2022',[]),('AI Minor 2024',[]),('T1229/41130',['41130','T1229'])])
def test_real_code_formats(text,expected):assert codes(text)==expected

@pytest.mark.parametrize('expression,interpretation',[
    (None,'unknown'),('-------','explicit_none'),('T1214','single_passed_course'),
    ('+ T1214','notation_unverified'),('T1229/41130','notation_unverified')])
def test_undefined_prerequisite_notation_is_not_guessed(expression,interpretation):
    assert cell_rule(expression)[0]==interpretation

def test_seven_plans_remain_separate(hebron_snapshot):
    assert len(plans())==7
    assert {p['id']:p['plan_year'] for p in plans()}['hu-cs-se-2026']==2026
    assert {p['id']:p['total_credits'] for p in plans()}['hu-cs-ai-2024']==138

def test_source_totals_are_not_sum_of_elective_listings(hebron_snapshot):
    cs=next(p for p in plans() if p['id']=='hu-cs-2022')
    rows=course_records(cs['id'])
    assert cs['total_credits']==135
    assert sum(r['credit_hours'] or 0 for r in rows)>135
    assert any(r['mandatory']==0 for r in rows) and any(r['mandatory']==1 for r in rows)
    assert json.loads(cs['warnings'])
    assert answer('What is the total credit-hour requirement for Computer Science 2022?',offline=True)['status']=='answered'
    assert '138' in answer('What is the total requirement for CS / Data Science and AI Minor 2024?',offline=True)['answer']
    references=retriever.search('What is the total credit-hour requirement for Computer Science 2022?',corpus='real')
    assert references and references[0]['document_id']=='hu-cs-2022'
    assert any(r['pdf_page']==1 for r in references)

def test_actual_printed_conflict_is_not_silently_resolved(hebron_snapshot):
    r=answer('كم ساعة 61101؟',plan_id='hu-cyber-2022',offline=True)
    assert r['status']=='needs_clarification'
    assert {c['pdf_page'] for c in r['citations']}=={1,2}

def test_actual_code_and_prerequisite_lookup(hebron_snapshot):
    result=answer('ما المتطلب السابق للمساق T1315؟',plan_id='hu-cs-2022',offline=True)
    assert result['origin']=='structured_db' and result['status']=='answered' and 'T1214' in result['answer']
    assert result['citations'][0]['document_id']=='hu-cs-2022' and result['citations'][0]['pdf_page']==3

def test_same_code_is_not_merged_across_plans(hebron_snapshot):
    rows=[r for r in course_records() if r['code']=='T1100']
    assert len({r['plan_id'] for r in rows})==7
    assert len({r['course_id'] for r in rows})==7

@pytest.mark.parametrize('q,id',[
    ('Which form is used to defer a semester?','hu-form-021'),
    ('Which form is used to appeal to the dean?','hu-form-027'),
    ('What document is used for course equivalency when transferring universities?','hu-form-022')])
def test_actual_form_catalog(q,id,hebron_snapshot):
    result=answer(q,offline=True)
    assert result['status']=='answered' and result['origin']=='structured_db'
    assert id in {c['document_id'] for c in result['citations']}
    assert all(c['pdf_page']==1 for c in result['citations'])

@pytest.mark.parametrize('q',[
    'What is the current official maximum withdrawal period?',
    'ما نسبة الحضور الإلزامية؟','ما المهلة الحالية لتأجيل فصل؟'])
def test_forms_and_conduct_do_not_establish_current_regulations(q,hebron_snapshot):
    result=answer(q,offline=True)
    assert result['status']=='insufficient_evidence' and 'غير موجودة' in result['answer']
    assert not result['citations']

def test_unknown_values_and_rows_are_not_claimed_verified(hebron_snapshot):
    result=answer('كم ساعة T1333؟',plan_id='hu-cs-2022',offline=True)
    assert result['status']=='insufficient_evidence' and result['origin']=='structured_db'
    result=answer('ما متطلب T1211؟',plan_id='hu-cs-ai-2024',offline=True)
    assert result['status']=='partially_answered' and 'لا أفترض' in result['answer']

def test_explicit_source_and_scope_filters_remain_enforced(hebron_snapshot):
    assert answer('Which form defers a semester?',document_id='hu-cs-2022',offline=True)['status']=='insufficient_evidence'
    assert answer('كم ساعة T1315؟',plan_id='hu-cs-2022',knowledge_scope='forms',offline=True)['status']=='insufficient_evidence'
    assert answer('What is the maximum withdrawal period?',knowledge_scope='conduct',offline=True)['status']=='insufficient_evidence'

def test_no_plan_or_student_record_means_no_graduation_decision(hebron_snapshot):
    assert answer('Can I graduate without listing completed courses?',offline=True)['status']=='needs_clarification'
    assert answer('ما متطلب T1315؟',offline=True)['status']=='needs_clarification'

def test_conduct_and_excluded_documents_are_isolated(hebron_snapshot):
    normal=retriever.search('ما أهداف مدونة السلوك؟',corpus='real')
    assert all(r['kind']!='conduct' for r in normal)
    conduct=retriever.search('ما أهداف مدونة السلوك؟',corpus='real',scope='conduct')
    assert conduct and all(r['kind']=='conduct' for r in conduct)
    assert not any(r['document_id'].startswith('hu-excluded-') for r in retriever.rows)
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM documents WHERE inclusion_status='excluded'").fetchone()[0]==3
        assert not db.execute('PRAGMA foreign_key_check').fetchall()

def test_sha_bound_reviews_fail_closed_when_record_missing(tmp_path,monkeypatch):
    import scripts.import_hebron as importer
    monkeypatch.setattr(importer,'ROOT',tmp_path)
    assert importer.source_hashes()['sha256']=={}
