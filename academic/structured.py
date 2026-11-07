"""Relational academic routing. Unreviewed extraction never becomes a fact."""
import json
import re
from rag import store
from rag.text import normalize, codes

def plans():
    with store.connect() as db:
        return [dict(r) for r in db.execute('''SELECT s.*,p.name_ar,p.name_en,d.program FROM study_plans s
            JOIN programs p ON p.id=s.program_id JOIN documents d ON d.id=s.document_id
            WHERE d.status='ready' AND d.inclusion_status='included' ORDER BY s.plan_year,s.title''')]

def row_evidence(reference_id):
    from rag.retrieval import retriever
    with store.connect() as db:
        reference=db.execute('SELECT * FROM source_references WHERE id=?',(reference_id,)).fetchone()
    if not reference:return []
    match=next((r for r in retriever.rows if r['id']==reference['chunk_id']),None)
    return [match] if match else []

def course_records(plan_id=None):
    with store.connect() as db:
        return [dict(r) for r in db.execute('''SELECT pc.*,c.code,c.code_key,c.name_ar,c.name_en,
             s.title AS plan_title,s.plan_year,s.version,d.program,s.document_id,
             pr.interpretation,pr.prerequisite_codes,pr.review_status AS rule_review_status,sr.chunk_id AS source_chunk_id
            FROM plan_courses pc JOIN courses c ON c.id=pc.course_id JOIN study_plans s ON s.id=pc.plan_id
            JOIN documents d ON d.id=s.document_id JOIN prerequisite_rules pr ON pr.plan_course_id=pc.id
            JOIN source_references sr ON sr.id=pc.source_reference_id
            WHERE d.status='ready' AND d.inclusion_status='included' AND (? IS NULL OR s.id=?)
            ORDER BY s.id,pc.id''',(plan_id,plan_id))]

def selected_plans(question, *, plan_id=None,program=None,version=None,document_id=None):
    available=plans()
    if plan_id:return [p for p in available if p['id']==plan_id]
    if document_id:return [p for p in available if p['document_id']==document_id]
    if program:available=[p for p in available if program in (p['program'],p['program_id'],p['name_ar'])]
    year=re.search(r'\b(20\d{2})\b',normalize(question))
    if version:available=[p for p in available if p['version']==version]
    elif year:available=[p for p in available if p['plan_year']==int(year.group(1))]
    n=normalize(question)
    # Program names are read from the DB; language aliases select a program,
    # never a factual answer, credit amount or prerequisite.
    aliases={
        'hu-cs':['علم الحاسوب','علوم الحاسوب','computer science','cs'],
        'hu-cs-ai':['علم البيانات','data science','data science and ai'],
        'hu-cs-se':['هندسة برمجيات','هندسه برمجيات','software engineering'],
        'hu-cs-business':['ادارة الاعمال','business administration'],
        'hu-web':['تكنولوجيا الويب','الوسائط المتعددة','web technology','multimedia'],
        'hu-cyber':['الامن السيبراني','cybersecurity','cyber security'],
        'hu-cybercrime':['جرائم','cybercrime','cybercrimes investigation']}
    matches=[]
    for p in available:
        found=[a for a in aliases.get(p['program_id'],[p['name_ar'],p['name_en']]) if normalize(a) in n]
        if found:matches.append((p,max(len(a) for a in found)))
    if matches:
        # Explicit minor/track names beat a generic major in the same question.
        specific=[m for m in matches if m[0]['program_id'] not in ('hu-cs','hu-cyber')]
        return [m[0] for m in (specific or matches)]
    return available

def form_records(query=''):
    with store.connect() as db:
        records=[dict(r) for r in db.execute('''SELECT f.*,d.title,d.version FROM academic_forms f
            JOIN documents d ON d.id=f.document_id WHERE d.status='ready' AND d.inclusion_status='included' ORDER BY f.form_number''')]
    if not query:return records
    n=normalize(query)
    ignored={'form','the','a','is','used','which','what','نموذج','ما','هو','اي','الذي','من','الى','في'}
    scored=[]
    for record in records:
        words=set(normalize(record['official_title']+' '+record['intended_use']+' '+record['keywords']).split())-ignored
        score=sum(1 for word in words if len(word)>2 and word in n)
        if record['form_number'] in n:score+=20
        if score:scored.append((score,record))
    scored.sort(key=lambda item:item[0],reverse=True)
    return [record for score,record in scored if score==scored[0][0]][:4] if scored else []

def route(question, *, plan_id=None,program=None,version=None,document_id=None,passed_courses=None):
    if not plans():return None
    n=normalize(question)
    is_graduation=bool(re.search(r'هل.*(?:اتخرج|تخرج)|(?:can|will|whether).*graduat|graduation readiness|جاهز.*تخرج',n))
    if is_graduation:
        chosen=selected_plans(question,plan_id=plan_id,program=program,version=version,document_id=document_id)
        evidence=row_evidence(chosen[0]['total_credits_reference']) if len(chosen)==1 else []
        return {'status':'needs_clarification','answer':'لا يمكن تحديد جاهزية التخرج دون خطة محددة ومراجعة بالكامل وقائمة المساقات المكتملة وحالتها في سجل افتراضي. الساعات الإجمالية وحدها لا تكفي، ولن أستخدم سجلاً حقيقياً أو أفترض اكتمال المتطلبات.', 'evidence':evidence}
    form_intent=bool(re.search(r'نموذج|نماذج|استماره|\bforms?\b|(?:which|what) document|ما (?:المستند|الوثيقه)',n))
    if form_intent:
        found=form_records(question)
        if document_id:found=[f for f in found if f['document_id']==document_id]
        if not found:return {'status':'insufficient_evidence','answer':'لم أجد نموذجاً موثقاً يطابق هذا الإجراء في الفهرس. لا يثبت غيابه أن الإجراء غير موجود.','evidence':[]}
        reviewed=[f for f in found if f['review_status']=='visual_checked_title_use']
        if not reviewed:return {'status':'needs_clarification','answer':'وجدت نموذجاً مستخرجاً لم تُراجع هويته بعد. راجع المصدر أولاً.','evidence':sum((row_evidence(f['source_reference_id']) for f in found),[])}
        lines=[f"نموذج {f['form_number']}: {f['official_title']}. الاستخدام: {f['intended_use']}." for f in reviewed]
        lines.append('هذا يثبت وجود النموذج وغرضه فقط؛ لا يثبت الأهلية أو مهلة حالية أو حق الموافقة. تاريخ النسخة غير محدد في الملفات المقدمة.')
        return {'status':'answered','answer':'\n\n'.join(lines),'evidence':sum((row_evidence(f['source_reference_id']) for f in reviewed),[])}
    asked_codes=set(codes(question))
    course_intent=bool(asked_codes) or bool(re.search(r'متطلب|prerequis|credit.*course|course.*credit|ساعات.*(?:مساق|ماده)|(?:مساق|ماده).*ساع|mandatory|elective|اجباري|اختياري|مساقات|\bcourses\b',n))
    total_intent=bool(re.search(r'total|اجمالي|مجموع|عدد.*ساعات.*(?:تخصص|خطه)|كم.*ساع.*(?:تخصص|خطه)|متطلبات.*(?:بكالوريوس|تخرج)',n))
    if not asked_codes and not total_intent and re.search(r'انسحاب|سحب|تاجيل|الحضور|الغياب|انذار|withdraw|attendance|deferr|registration.limit',n):
        return None
    if not course_intent and not total_intent:return None
    chosen=selected_plans(question,plan_id=plan_id,program=program,version=version,document_id=document_id)
    if len(chosen)!=1:
        return {'status':'needs_clarification','answer':'حدد الخطة والبرنامج والسنة؛ لا يمكن دمج متطلبات المساق أو الساعات بين الخطط. الخطط المتاحة: '+ '؛ '.join(p['id']+' — '+p['title'] for p in chosen), 'evidence':[]}
    plan=chosen[0]
    if total_intent and not asked_codes:
        evidence=row_evidence(plan['total_credits_reference'])
        if plan['total_credits'] is None or not plan['review_status'].startswith('visual_checked'):
            return {'status':'insufficient_evidence','answer':'لم يُتحقق من إجمالي ساعات هذه الخطة في المصدر بعد.','evidence':evidence}
        warnings=json.loads(plan['warnings'])
        text=f"الإجمالي المعلن في خطة {plan['title']} هو {plan['total_credits']:g} ساعة معتمدة. هذا إجمالي الخطة المطبوع، وليس جمع كل المساقات الاختيارية المدرجة، ولا يثبت جاهزية طالب للتخرج."
        if warnings:text+=' توجد ملاحظة تعارض في أرقام المتطلبات الفرعية بالمصدر؛ يلزم الرجوع للجامعة ولا أصحح الأرقام بالافتراض.'
        return {'status':'answered','answer':text,'evidence':evidence}
    rows=course_records(plan['id'])
    matched=[r for r in rows if r['code_key'] in asked_codes or (not asked_codes and
        any(len(normalize(name or ''))>3 and normalize(name) in n for name in (r['name_ar'],r['name_en'])))]
    if not matched:return {'status':'insufficient_evidence','answer':'لم أجد هذا المساق بشكل موثق في الخطة المحددة. تحقق من رمز المساق أو اختر الخطة المناسبة.','evidence':[]}
    if len({r['code_key'] for r in matched})>1:
        return {'status':'needs_clarification','answer':'حدد مساقاً واحداً لحساب متطلباته أو ساعاته.','evidence':[]}
    signatures={(r['credit_hours'],r['prerequisite_expression']) for r in matched}
    evidence=sum((row_evidence(r['source_reference_id']) for r in matched),[])
    if len(signatures)>1:return {'status':'needs_clarification','answer':'توجد صفوف مختلفة لهذا الرمز داخل الخطة؛ لا يمكن اعتماد أحدها تلقائياً. راجع الصفوف الأصلية.','evidence':evidence}
    row=next((r for r in matched if r['review_status']=='visual_checked_core_fields'),matched[0])
    if row['review_status']!='visual_checked_core_fields':
        return {'status':'insufficient_evidence','answer':f"وجدت صف المساق {row['code']}، لكن بياناته لم تُراجع بصرياً بعد. لا أعتمد رقماً أو شرطاً غير متحقق منه؛ افتح المصدر أو راجع قائمة المراجعة.",'evidence':evidence}
    if any(k in n for k in ['ساع','credit','hours']):
        return {'status':'answered','answer':f"المساق {row['code']} في خطة {plan['title']}: {row['credit_hours']:g} ساعة معتمدة. الاسم المستخرج من الجدول: {row['name_ar']} / {row['name_en']} (الاسم يحتاج مراجعة مستقلة).",'evidence':evidence}
    expression=row['prerequisite_expression']
    if row['interpretation'] in ('unknown','notation_unverified'):
        return {'status':'partially_answered','answer':f"خانة المتطلب للمساق {row['code']} كما وردت: {expression or '[فارغة]'}. لا توجد في الملفات المقدمة قاعدة موثقة تفسر الخانة الفارغة أو الرموز؛ لا أفترض عدم وجود متطلب أو معنى الجمع/التزامن أو البدائل.",'evidence':evidence}
    prerequisite_codes=json.loads(row['prerequisite_codes'])
    text=(f"المتطلب السابق للمساق {row['code']} في خطة {plan['title']}: "+
          ('لا يوجد رمز متطلب؛ الخانة تحتوي شرطات صريحة.' if row['interpretation']=='explicit_none' else expression+'.'))
    eligibility=any(k in n for k in ['اسجل','eligible','register'])
    if eligibility:
        if passed_courses is None and prerequisite_codes:
            return {'status':'needs_clarification','answer':text+' هل اجتزت المتطلب في الحالة الافتراضية؟ لا ترسل سجلاً حقيقياً.','evidence':evidence}
        missing=sorted(set(prerequisite_codes)-set(passed_courses or []))
        return {'status':'partially_answered','answer':text+(' لم يتحقق المتطلب في الحالة الافتراضية.' if missing else ' تحقق شرط رموز المتطلبات في الحالة الافتراضية.')+' هذا ليس قرار أهلية تسجيل كامل؛ اللوائح الأكاديمية الحالية غير متوفرة.',
                'evidence':evidence,'prerequisites_satisfied':not missing,'missing':missing}
    return {'status':'answered','answer':text,'evidence':evidence}
