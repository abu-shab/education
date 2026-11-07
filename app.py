from contextlib import asynccontextmanager
from pathlib import Path
import json
import shutil
import threading
import uuid
from urllib.parse import urlparse
from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
from typing import Literal
from config import ROOT, DATA, MAX_UPLOAD
from rag import store
from rag.ingestion import ingest
from rag.retrieval import retriever
from rag.service import answer, citation
from providers.gemini import configuration

mutation_lock = threading.Lock()

@asynccontextmanager
async def lifespan(app):
    store.init()
    retriever.refresh()
    yield

app = FastAPI(title='ACADEMIA AI — Smart Academic Advisor', lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['localhost', '127.0.0.1', '[::1]', 'testserver'])
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')
templates = Jinja2Templates(directory=str(ROOT / 'templates'))

@app.middleware('http')
async def protect_local(request: Request, call_next):
    if request.method in ('POST', 'PUT', 'DELETE'):
        origin = request.headers.get('origin')
        if origin and origin.rstrip('/') != str(request.base_url).rstrip('/'):
            return JSONResponse({'detail': 'مصدر الطلب غير مسموح.'}, status_code=403)
        if request.headers.get('sec-fetch-site') == 'cross-site':
            return JSONResponse({'detail': 'مصدر الطلب غير مسموح.'}, status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    return response

@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    return JSONResponse({'detail': 'تعذرت العملية. راجع حالة المستندات أو أعد المحاولة.'}, status_code=500)

@app.get('/', response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request=request, name='index.html', context={})

@app.get('/api/status')
def status():
    docs = store.documents()
    with store.connect() as db:
        calls = db.execute("SELECT count(*) FROM usage WHERE date(created_at)=date('now')").fetchone()[0]
    from academic.structured import plans,course_records,form_records
    actual_plans=plans();actual_courses=course_records()
    return {'documents': len(docs), 'ready': sum(d['status']=='ready' for d in docs),
            'chunks': len(retriever.rows), 'genuine_documents': sum(not d['synthetic'] and d['status']=='ready' for d in docs),
            'genuine_chunks':sum(not r['synthetic'] for r in retriever.rows),
            'embedding': retriever.embedding_status, 'semantic_enabled': retriever.vectors is not None,
            'gemini': configuration(), 'api_attempts_today_utc': calls,
            'study_plans':len(actual_plans),'academic_forms':len(form_records()),
            'verified_course_records':sum(c['review_status']=='visual_checked_core_fields' for c in actual_courses),
            'unverified_course_records':sum(c['review_status']!='visual_checked_core_fields' for c in actual_courses),
            'current_academic_regulations_available':any(not d['synthetic'] and d['kind'] in ('regulations','handbook','exams') and d['status']=='ready' for d in docs)}

@app.get('/api/documents')
def documents():
    return [{k:v for k,v in d.items() if k not in ('filename','sha256')} for d in store.documents()]

@app.post('/api/documents')
def upload(file: UploadFile = File(...), title: str = Form(..., max_length=180),
           version: str = Form('', max_length=80), program: str = Form('', max_length=80),
           effective_date: str = Form('', max_length=20), synthetic: bool = Form(False),
           kind: Literal['regulations','plan','handbook','exams','schedule','form','conduct'] = Form('regulations'),
           public_confirmed: bool = Form(False)):
    if not public_confirmed:
        raise HTTPException(400, 'أكد أن المستند عام أو خيالي ولا يحتوي بيانات طلاب خاصة.')
    if not title.strip():
        raise HTTPException(400, 'عنوان المستند مطلوب.')
    suffix = Path(file.filename or '').suffix.lower()
    if suffix not in ('.pdf', '.txt', '.docx'):
        raise HTTPException(400, 'ارفع PDF أو TXT أو DOCX فقط.')
    doc_id = uuid.uuid4().hex[:16]
    path = DATA / 'uploads' / (doc_id + suffix)
    try:
        size = 0
        with path.open('wb') as target:
            while block := file.file.read(65536):
                size += len(block)
                if size > MAX_UPLOAD:
                    raise ValueError('تجاوز الملف الحد الأقصى للحجم (15 MB افتراضياً).')
                target.write(block)
        if size == 0:
            raise ValueError('الملف فارغ.')
        signature = path.read_bytes()[:8]
        if suffix == '.pdf' and not signature.startswith(b'%PDF-'):
            raise ValueError('توقيع PDF غير صالح.')
        if suffix == '.docx' and not signature.startswith(b'PK'):
            raise ValueError('توقيع DOCX غير صالح.')
        with mutation_lock:
            id, count = ingest(path, title=title.strip(), version=version, program=program,
                               effective_date=effective_date, synthetic=synthetic, kind=kind, doc_id=doc_id)
            retriever.refresh()
        return {'id': id, 'chunks': count, 'status': 'ready'}
    except ValueError as exc:
        path.unlink(missing_ok=True)
        raise HTTPException(400, str(exc)) from None
    except Exception:
        path.unlink(missing_ok=True)
        raise HTTPException(400, 'تعذر استخراج المستند. تحقق من الملف وترميزه ومحتواه النصي.') from None
    finally:
        file.file.close()

@app.post('/api/documents/{id}/reindex')
def reindex(id: str):
    doc = next((d for d in store.documents() if d['id']==id), None)
    if not doc:
        raise HTTPException(404, 'المستند غير موجود.')
    with mutation_lock:
        try:
            if doc['original_filename'] and id.startswith('hu-'):
                from scripts.import_hebron import main as import_hebron
                if import_hebron()!=0:raise ValueError('Some sources failed; see manifest')
            else:
                ingest(DATA / 'uploads' / doc['filename'], title=doc['title'], version=doc['version'],
                       program=doc['program'], effective_date=doc['effective_date'], synthetic=bool(doc['synthetic']), kind=doc['kind'], doc_id=id)
            retriever.refresh()
        except Exception:
            raise HTTPException(400, 'تعذرت إعادة الفهرسة. تحقق من المستند الأصلي.') from None
    return {'status':'ready'}

@app.delete('/api/documents/{id}')
def delete_document(id: str):
    doc = next((d for d in store.documents() if d['id']==id), None)
    if not doc:
        raise HTTPException(404, 'المستند غير موجود.')
    with mutation_lock:
        with store.connect() as db:
            db.execute('DELETE FROM documents WHERE id=?', (id,))
        path = (DATA / 'uploads' / doc['filename']).resolve()
        if path.parent == (DATA / 'uploads').resolve():
            path.unlink(missing_ok=True)
        retriever.refresh()
    return {'deleted': True}

class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1500)
    mode: Literal['generate','retrieve'] = 'generate'
    history: list[str] = Field(default_factory=list, max_length=6)
    program: str | None = Field(default=None, max_length=80)
    version: str | None = Field(default=None, max_length=80)
    document_id: str | None = Field(default=None, max_length=80)
    corpus: Literal['auto','synthetic','real'] = 'auto'
    plan_id: str | None = Field(default=None,max_length=80)
    knowledge_scope: Literal['academic','conduct','forms','all'] = 'academic'

@app.post('/api/chat')
def chat(body: ChatRequest):
    if any(len(q)>1500 for q in body.history):
        raise HTTPException(400, 'سياق المحادثة طويل جداً.')
    args = body.model_dump()
    return answer(**args)

@app.get('/api/courses')
def courses():
    from academic.structured import course_records,row_evidence
    records=course_records()
    if records:
        result=[]
        source_rows={r['id']:r for r in retriever.rows}
        for r in records:
            evidence=[source_rows[r['source_chunk_id']]] if r['source_chunk_id'] in source_rows else []
            if not evidence:continue
            result.append({'code':r['code'],'name':r['name_ar'],'name_en':r['name_en'],
                'credits':r['credit_hours'],'prerequisites':r['prerequisite_expression'] or 'غير معروف (خانة فارغة)',
                'program':r['program'],'version':r['version'],'plan_id':r['plan_id'],'plan_year':r['plan_year'],
                'requirement_category':r['requirement_category'],'mandatory':r['mandatory'],
                'review_status':r['review_status'],'verified_fields':json.loads(r['verified_fields']),
                'synthetic':False,'citation':citation(evidence[0])})
        return result
    return [{**r['course'], 'program':r['program'], 'version':r['version'],
             'synthetic':bool(r['synthetic']), 'citation':citation(r)} for r in retriever.rows if r.get('course')]

class PrerequisiteRequest(BaseModel):
    course_code: str = Field(max_length=20)
    program: str = Field(max_length=80)
    version: str = Field(max_length=80)
    passed_courses: list[str] | None = Field(default=None, max_length=100)
    corpus: Literal['auto','synthetic','real'] = 'auto'
    plan_id: str | None = Field(default=None,max_length=80)

@app.post('/api/prerequisites')
def prerequisites(body: PrerequisiteRequest):
    from rag.text import codes
    passed = None if body.passed_courses is None else codes(' '.join(body.passed_courses))
    return answer('هل بقدر أسجل ' + body.course_code + '؟', passed_courses=passed,
                  program=body.program, version=body.version, corpus=body.corpus,plan_id=body.plan_id)

@app.get('/api/plans')
def study_plans():
    from academic.structured import plans
    return plans()

@app.get('/api/forms')
def academic_forms(q: str=''):
    from academic.structured import form_records,row_evidence
    return [{**f,'citation':citation(e[0]) if (e:=row_evidence(f['source_reference_id'])) else None} for f in form_records(q)]

@app.get('/api/review-queue')
def review_queue():
    with store.connect() as db:
        rows=[dict(r) for r in db.execute('''SELECT q.id,q.document_id,q.plan_course_id,q.source_reference_id,q.reason,q.status,
            s.pdf_page,s.chunk_id,d.title FROM review_queue q JOIN documents d ON d.id=q.document_id
            LEFT JOIN source_references s ON s.id=q.source_reference_id ORDER BY q.id''')]
    return rows

@app.get('/api/source-manifest')
def source_manifest():
    path=DATA/'source_manifest.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'files':[]}

@app.get('/sources/{id}', response_class=HTMLResponse)
def source(id: str, request: Request):
    row = next((r for r in retriever.rows if r['id']==id), None)
    if not row:
        raise HTTPException(404, 'المصدر غير موجود.')
    return templates.TemplateResponse(request=request, name='source.html', context={'source':citation(row)})

@app.get('/api/documents/{id}/file')
def original(id: str):
    doc = next((d for d in store.documents() if d['id']==id), None)
    if not doc:
        raise HTTPException(404, 'المستند غير موجود.')
    path = (DATA / 'uploads' / doc['filename']).resolve()
    if path.parent != (DATA / 'uploads').resolve() or not path.exists():
        raise HTTPException(404, 'الملف الأصلي غير موجود.')
    return FileResponse(path, filename=doc['title'] + path.suffix, content_disposition_type='inline',
                        media_type='application/pdf' if path.suffix=='.pdf' else None)

@app.get('/api/evaluation')
def evaluation_results():
    path = DATA / 'evaluation_results.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'status':'not_run','cases':[]}

@app.post('/api/evaluation/run')
def run_evaluation():
    from evaluation.run import run
    if not mutation_lock.acquire(blocking=False):
        raise HTTPException(409, 'عملية فهرسة قيد التنفيذ. أعد المحاولة بعد انتهائها.')
    try:
        return run()
    finally:
        mutation_lock.release()
