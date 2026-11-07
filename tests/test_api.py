import pytest
from fastapi.testclient import TestClient
from app import app
from config import ROOT

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_all_views_and_status(client):
    r=client.get('/')
    assert r.status_code==200
    for name in ['dashboard','chat','plans','library','evaluation']:
        assert f'id="{name}"' in r.text
    assert client.get('/api/status').json()['genuine_documents']==0
    assert 'script-src' in r.headers['Content-Security-Policy']

def test_cross_origin_mutation_blocked(client):
    r=client.post('/api/chat',headers={'Origin':'https://untrusted.example'},json={'question':'ما الحضور؟','mode':'retrieve'})
    assert r.status_code==403

def test_chat_works_without_privacy_confirmation(client):
    r=client.post('/api/chat',json={'question':'كم ساعة CS102؟'})
    assert r.status_code==200
    assert r.json()['status']=='answered' and r.json()['origin']=='deterministic'

def test_request_bounds(client):
    assert client.post('/api/chat',json={'question':'x'*1501}).status_code==422
    assert client.post('/api/chat',json={'question':'hi','history':['a'*1600],'mode':'retrieve'}).status_code==400

def test_rules_guide_cannot_be_indexed(client):
    path=ROOT/'IEEE_RAG_Student_Guide_Academic_Advisor_AR.pdf'
    if path.exists():
        content=path.read_bytes()
    else:
        import pymupdf
        doc=pymupdf.open();doc.new_page().insert_text((50,50),'IEEE RAG Hackathon - participant guide, not regulations.')
        content=doc.tobytes()
    r=client.post('/api/documents',data={'title':'Wrong source','public_confirmed':'true'},files={'file':('guide.pdf',content,'application/pdf')})
    assert r.status_code==400 and 'المسابقة' in r.json()['detail']

def test_upload_validation(client):
    r=client.post('/api/documents',data={'title':'x','public_confirmed':'true'},files={'file':('evil.pdf',b'not a pdf','application/pdf')})
    assert r.status_code==400
    r=client.post('/api/documents',data={'title':'x'},files={'file':('file.txt',b'public text','text/plain')})
    assert r.status_code==400
    r=client.post('/api/documents',data={'title':'x','public_confirmed':'true'},files={'file':('file.exe',b'MZ','application/octet-stream')})
    assert r.status_code==400

def test_source_metadata_and_escape(client):
    r=client.get('/sources/demo-regs-p1-1')
    assert r.status_code==200 and 'ليست صفحة PDF' in r.text
    assert client.get('/sources/not-found').status_code==404

def test_upload_reindex_and_delete(client):
    r=client.post('/api/documents',data={'title':'<script>alert(1)</script>','public_confirmed':'true','synthetic':'true'},
        files={'file':('../../traversal.txt','المادة 1: نص خيالي للفحص فقط'.encode('utf-8'),'text/plain')})
    assert r.status_code==200
    id=r.json()['id']
    assert client.post(f'/api/documents/{id}/reindex').status_code==200
    rows=client.get('/api/documents').json()
    assert all('filename' not in row for row in rows)
    assert client.get(f'/api/documents/{id}/file').status_code==200
    assert client.delete(f'/api/documents/{id}').status_code==200
    assert client.get(f'/api/documents/{id}/file').status_code==404

def test_prerequisite_api(client):
    r=client.post('/api/prerequisites',json={'course_code':'CS102','program':'DEMO-CS','version':'DEMO-2026','passed_courses':['CS101']})
    assert r.status_code==200 and r.json()['prerequisites_satisfied']

def test_pdf_upload_source_page_and_original(client):
    import pymupdf
    doc=pymupdf.open();doc.new_page().insert_text((50,50),'Article 12: Synthetic fixture. Attendance is 81 percent.')
    r=client.post('/api/documents',data={'title':'Fictional PDF test','public_confirmed':'true','synthetic':'true'},
        files={'file':('fixture.pdf',doc.tobytes(),'application/pdf')})
    assert r.status_code==200
    id=r.json()['id']
    from rag.retrieval import retriever
    row=next(c for c in retriever.rows if c['document_id']==id)
    source=client.get('/sources/'+row['id'])
    assert source.status_code==200 and 'صفحة PDF: 1' in source.text and 'Article 12' in source.text
    original=client.get(f'/api/documents/{id}/file')
    assert original.content.startswith(b'%PDF-')
    assert client.delete(f'/api/documents/{id}').status_code==200
