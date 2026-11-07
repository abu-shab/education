import re
from academic.rules import resolve_question, evaluate_course, evaluate_registration
from providers.gemini import provider, ProviderUnavailable
from rag.retrieval import retriever
from rag.text import normalize, codes
from rag.language import detect_language,localize_message,ERRORS_EN

def citation(r):
    return {'id': r['id'], 'document_id': r['document_id'], 'document': r['title'],
            'pdf_page': r.get('pdf_page'), 'page': r['page'], 'page_end': r.get('page_end'),
            'printed_page': r.get('printed_page'), 'article': r.get('article'), 'version': r['version'],
            'program': r['program'], 'synthetic': bool(r['synthetic']), 'excerpt': r['text'],
            'effective_date': r.get('effective_date'),
            'url': '/sources/' + r['id'], 'score': r.get('score')}

def answer(question, *, mode='generate', history=None, passed_courses=None, program=None, version=None, document_id=None, corpus='auto', offline=False, plan_id=None, knowledge_scope='academic'):
    language=detect_language(question,history)
    q, clarification = resolve_question(question, history or [])
    base = {'resolved_question': q, 'citations': [], 'claims': [], 'origin': 'guardrail', 'synthetic': False,'language':language}
    def result(status, text, evidence=None, origin='guardrail', **extra):
        refs = list({r['id']: r for r in (evidence or [])}.values())
        return {**base, 'status': status, 'answer': localize_message(text,language), 'citations': [citation(r) for r in refs],
                'origin': origin, 'synthetic': bool(refs) and all(r['synthetic'] for r in refs), **extra}
    if clarification:
        return result('needs_clarification', clarification)
    n = normalize(q)
    if re.search(r'تجاهل.*(?:تعليمات|سابق)|ignore.*(?:instruction|previous)|system prompt|api.?key|مفتاح.*api', n):
        return result('out_of_scope', 'لا أنفذ تعليمات لتغيير قواعد الاستناد إلى الأدلة أو كشف أسرار الخدمة.')
    if re.search(r'قصيد|اغنيه|نكت|شعر|poem|write.*code|recipe', n):
        return result('out_of_scope', 'أساعدك في الأسئلة الأكاديمية التي تغطيها المستندات المتاحة فقط.')
    if re.search(r'[\w.+-]+@[\w.-]+\.[a-z]{2,}|\b\d{8,}\b', q, re.I):
        return result('needs_clarification', 'احذف الأسماء والأرقام الشخصية والبريد، واستخدم حالة افتراضية فقط.')
    from academic import structured
    real_available=bool(structured.plans()) and corpus!='synthetic'
    conduct_question=bool(re.search(r'سلوك|مدونه|conduct|ethics code',n)) and not codes(q)
    scope='conduct' if conduct_question else knowledge_scope
    if document_id and any(r['document_id']==document_id and r['kind']=='conduct' for r in retriever.rows):scope='conduct'
    evidence = retriever.search(q, limit=8, document_id=document_id, program=program, version=version, corpus=corpus,scope=scope,plan_id=plan_id)
    if mode == 'retrieve':
        return result('retrieved' if evidence else 'insufficient_evidence',
                      'هذه مقاطع بحث أصلية فقط؛ لم تُولّد إجابة بواسطة Gemini.' if evidence else 'لم أجد أدلة كافية في المستندات.', evidence, 'retrieval_only')
    policy_question=bool(re.search(r'حضور|غياب|انسحاب|سحب|تاجيل|تسجيل|اسجل|انذار|اعاده.*مساق|حد.*ساع|ساعات.*مسموح|withdraw|attendance|absence|registration|register|enroll|credit.limit|(?:max|min)(?:imum)?.*(?:credit|hours)|deferr',n))
    form_question=bool(re.search(r'نموذج|نماذج|استماره|\bforms?\b|(?:which|what) document',n))
    if real_available and scope=='conduct' and policy_question and not form_question:
        return result('insufficient_evidence','مدونة السلوك ليست لائحة أكاديمية تحدد المهل أو الأهلية. اللوائح الأكاديمية الحالية غير موجودة في الحزمة المقدمة؛ لا أستنتج منها قواعد تسجيل أو انسحاب أو حضور.')
    if real_available and scope!='conduct':
        if scope=='forms' and not form_question:
            return result('insufficient_evidence','نطاق البحث المحدد هو النماذج الإجرائية فقط. لا تثبت النماذج ساعات المساقات أو متطلباتها أو اللوائح الحالية.')
        routed=structured.route(q,plan_id=plan_id,program=program,version=version,document_id=document_id,passed_courses=passed_courses,language=language)
        if routed:
            return result(routed['status'],routed['answer'],routed['evidence'],'structured_db',
                **{k:v for k,v in routed.items() if k not in ('status','answer','evidence')})
        if policy_question:
            evidence=retriever.search(q,limit=8,document_id=document_id,program=program,version=version,
                corpus='real',scope='academic',kinds=['regulations','handbook','exams'])
            if not evidence:
                return result('insufficient_evidence','اللوائح الأكاديمية الحالية المنظمة لهذا السؤال غير موجودة في الحزمة المقدمة. الخطط والنماذج ومدونة السلوك لا تثبت حد الانسحاب أو الحضور أو التسجيل الحالي. راجع دائرة القبول والتسجيل؛ لا يمكنني افتراض مهلة أو شرط.')
    # Refuse to infer a dynamic exam date from generic exam regulations.
    if re.search(r'متي|موعد|اي يوم|when|what date', n) and re.search(r'امتحان|اختبار|exam', n) and not any(r['kind'] == 'schedule' for r in evidence):
        return result('insufficient_evidence', 'لا يتوفر جدول امتحانات موثق يجيب عن الموعد. راجع جدول الامتحانات الرسمي أو دائرة التسجيل.')
    groups = {}
    for r in evidence:
        groups.setdefault((r['program'], r['kind']), set()).add(r['version'])
    if not version and not document_id and any(len(v) > 1 for v in groups.values()):
        return result('needs_clarification', 'توجد نسخ مختلفة من اللوائح أو الخطط. حدد البرنامج ونسخة المستند التي تنطبق عليك.', evidence)
    course_rows = retriever.rows if not document_id else [r for r in retriever.rows if r['document_id'] == document_id]
    multi_topic = any(k in n for k in ['انسحاب', 'الحضور', 'الغياب']) and any(k in n for k in ['cs', 'برمجة', 'مساق'])
    deterministic = None if multi_topic or real_available else evaluate_course(q, course_rows, passed_courses, program, version, corpus,language=language)
    if not deterministic:
        deterministic = evaluate_registration(q, evidence,language=language)
    if deterministic:
        return result(deterministic['status'], deterministic['answer'], deterministic['evidence'], 'deterministic',
            **{k:v for k,v in deterministic.items() if k not in ('status','answer','evidence')})
    if not evidence:
        return result('insufficient_evidence', 'لا أجد معلومات موثقة تكفي للإجابة. حدد السؤال أو أضف المستند الأكاديمي المناسب.')
    # Eligibility calculations are never delegated to the language model.
    if any(x in n for x in ['هل اتخرج', 'بقدر اتخرج', 'هل استطيع التخرج', 'هل يحق لي التسجيل']):
        return result('needs_clarification', 'لا يمكن تأكيد الأهلية الكاملة من هذه الأدلة. يلزم مراجعة جميع متطلبات الخطة واللوائح مع المرشد، دون إرسال سجل طالب حقيقي.', evidence)
    if offline:
        return result('service_unavailable', 'التوليد متوقف في التقييم المحلي؛ هذه أدلة فقط.', evidence, 'retrieval_only')
    try:
        generated, usage = provider.generate(q, evidence,language=language)
        cited_ids = {id for c in generated.claims for id in c.evidence_ids}
        refs = [r for r in evidence if r['id'] in cited_ids]
        claims = [c.model_dump() for c in generated.claims]
        text = '\n\n'.join(c['text'] for c in claims)
        if generated.message:
            text += ('\n\n' if text else '') + generated.message
        return result(generated.status, text, refs, 'gemini', claims=claims, usage=usage)
    except ProviderUnavailable as exc:
        message=ERRORS_EN.get(exc.code,ERRORS_EN['service_unavailable']) if language=='en' else str(exc)
        return result('service_unavailable', message, evidence, 'retrieval_only', error_code=exc.code)
