"""Source-derived deterministic checks; no model controls eligibility or arithmetic."""
import re
from rag.text import normalize, codes

def resolve_question(question, history):
    q = normalize(question)
    if history and re.match(r'^(واذا|طيب|وإن|واذا|و لو|واذا صار)', q):
        previous = history[-1]
        if not re.search(r'\d+(?:\.\d+)?', q):
            return question, 'حدد المعدل الجديد بالأرقام لإعادة البحث؛ لا يمكن افتراض معنى «أعلى». '
        if 'معدل' in normalize(previous):
            value = re.search(r'\d+(?:\.\d+)?', q).group()
            return re.sub(r'(معدلي\s*)[\d٠-٩.]+', lambda m: m.group(1)+value, previous) + ' ' + question, None
        return previous + '\nسؤال المتابعة: ' + question, None
    return question, None

def scoped_courses(rows, program=None, version=None, corpus='auto'):
    real = any(not r['synthetic'] for r in rows)
    return [r for r in rows if r.get('course')
            and (not program or r['program'] == program) and (not version or r['version'] == version)
            and (corpus == 'all' or (bool(r['synthetic']) if corpus == 'synthetic' or (corpus == 'auto' and not real) else not r['synthetic']))]

def evaluate_course(question, rows, passed_courses=None, program=None, version=None, corpus='auto'):
    q = normalize(question)
    all_courses = scoped_courses(rows, program, version, corpus)
    requested = set(codes(question))
    matches = [r for r in all_courses if r['course']['code'] in requested
               or normalize(r['course']['name']) in q]
    if not matches:
        return None
    variants = {(r['program'], r['version'], r['course']['code']) for r in matches}
    definitions = {(r['course']['credits'], r['course']['prerequisites']) for r in matches}
    if len(variants) > 1 or len(definitions) > 1:
        return {'status': 'needs_clarification', 'answer': 'أي برنامج ونسخة خطة تقصد؟ توجد عدة خطط أو مساقات متطابقة.', 'evidence': matches}
    source = matches[0]
    course = source['course']
    chain = []
    seen = set()
    def visit(c):
        if c['code'] in seen:
            return
        seen.add(c['code'])
        for code in c['prerequisite_codes']:
            other = next((r for r in all_courses if r['course']['code'] == code
                and r['version'] == source['version'] and r['program'] == source['program']), None)
            if other:
                chain.append(other)
                visit(other['course'])
    visit(course)
    evidence = [source] + list({r['id']: r for r in chain}.values())
    if any(k in q for k in ['ساع', 'credit']):
        return {'status': 'answered', 'answer': f"عدد الساعات المعتمدة لمساق {course['name']} ({course['code']}): {course['credits']:g}.", 'evidence': [source]}
    if any(k in q for k in ['اسجل', 'تسجيل', 'متطلب', 'شرط', 'prerequisite', 'eligible']):
        base = f"المتطلبات السابقة للمساق {course['name']} ({course['code']}): {course['prerequisites']}."
        if not course['simple_prerequisites']:
            return {'status': 'needs_clarification', 'answer': base + ' يتضمن الشرط تفاصيل تحتاج مراجعة بشرية؛ لا يمكن حساب الأهلية آلياً.', 'evidence': evidence}
        if not any(k in q for k in ['اسجل', 'تسجيل', 'eligible']):
            return {'status': 'answered', 'answer': base, 'evidence': evidence}
        if passed_courses is None and course['prerequisite_codes']:
            return {'status': 'needs_clarification', 'answer': base + ' هل اجتزت هذه المتطلبات؟ أدخل فقط قائمة افتراضية في فاحص المتطلبات.', 'evidence': evidence}
        missing = sorted(set(course['prerequisite_codes']) - set(passed_courses or []))
        return {'status': 'partially_answered', 'answer': base + (' لم يتحقق شرط المتطلبات السابقة في الملف الافتراضي: ' + '، '.join(missing)
            if missing else ' تحقق شرط المتطلبات السابقة في الملف الافتراضي.') + ' هذه نتيجة فحص المتطلبات فقط؛ أهلية التسجيل الكاملة تتطلب اللوائح والموافقات الأخرى.',
            'prerequisites_satisfied': not missing, 'missing': missing, 'evidence': evidence}
    return None

def evaluate_registration(question, evidence):
    q = normalize(question)
    if not ('معدل' in q and any(k in q for k in ['ساع', 'اسجل', 'تسجيل'])):
        return None
    gpa = re.search(r'معدل(?:ي)?\s*(?:هو|يساوي)?\s*([\d.]+)', q)
    if not gpa:
        return {'status': 'needs_clarification', 'answer': 'ما المعدل الافتراضي بالأرقام؟', 'evidence': []}
    try:
        value = float(gpa.group(1))
    except ValueError:
        return {'status': 'needs_clarification', 'answer': 'اكتب المعدل الافتراضي كرقم صالح مثل 2.8.', 'evidence': []}
    if not 0 <= value <= 4:
        return {'status': 'needs_clarification', 'answer': 'الجدول التجريبي يستخدم مقياس 0 إلى 4؛ حدد المقياس المناسب لوثيقتك.', 'evidence': []}
    matched = [r for r in evidence if r.get('registration_rule') and
        r['registration_rule']['gpa_min'] <= value < r['registration_rule']['gpa_max']]
    if not matched:
        return None
    conditions = {(r['registration_rule']['min_credits'], r['registration_rule']['max_credits'], r['registration_rule']['conditions']) for r in matched}
    if len(conditions) > 1:
        return {'status': 'needs_clarification', 'answer': 'توجد قواعد تسجيل مختلفة؛ حدد نسخة اللائحة والبرنامج.', 'evidence': matched}
    rule = matched[0]['registration_rule']
    return {'status': 'partially_answered', 'answer': f"حسب صف المعدل {value:g}: الحد الأدنى {rule['min_credits']:g} والأقصى {rule['max_credits']:g} ساعة. الشروط: {rule['conditions']}. لا يثبت هذا وحده أهلية التسجيل؛ يجب التحقق من جميع الشروط.", 'evidence': matched[:1]}
