"""Source-derived deterministic checks; no model controls eligibility or arithmetic."""
import re
from rag.text import normalize, codes
from rag.language import choose

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

def evaluate_course(question, rows, passed_courses=None, program=None, version=None, corpus='auto',language='ar'):
    def m(ar,en):return choose(ar,en,language)
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
        return {'status': 'needs_clarification', 'answer': m('أي برنامج ونسخة خطة تقصد؟ توجد عدة خطط أو مساقات متطابقة.','Which program and plan version do you mean? Multiple plans or matching courses are available.'), 'evidence': matches}
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
    if any(k in q for k in ['ساع', 'credit','hours']):
        return {'status': 'answered', 'answer': m(f"عدد الساعات المعتمدة لمساق {course['name']} ({course['code']}): {course['credits']:g}.",f"Course {course['code']} has {course['credits']:g} credit hours."), 'evidence': [source]}
    if any(k in q for k in ['اسجل', 'تسجيل', 'متطلب', 'شرط', 'prerequisite', 'eligible','register']):
        requirements=course['prerequisites']
        if language=='en' and requirements in ('لا يوجد','-'):requirements='none listed'
        base = m(f"المتطلبات السابقة للمساق {course['name']} ({course['code']}): {course['prerequisites']}.",f"Prerequisites for course {course['code']}: {requirements}.")
        if not course['simple_prerequisites']:
            return {'status': 'needs_clarification', 'answer': base + m(' يتضمن الشرط تفاصيل تحتاج مراجعة بشرية؛ لا يمكن حساب الأهلية آلياً.',' The condition includes details requiring human review; eligibility cannot be calculated automatically.'), 'evidence': evidence}
        if not any(k in q for k in ['اسجل', 'تسجيل', 'eligible','register']):
            return {'status': 'answered', 'answer': base, 'evidence': evidence}
        if passed_courses is None and course['prerequisite_codes']:
            return {'status': 'needs_clarification', 'answer': base + m(' هل اجتزت هذه المتطلبات؟ أدخل فقط قائمة افتراضية في فاحص المتطلبات.',' Have you passed these prerequisites? Enter only a fictional list in the prerequisite checker.'), 'evidence': evidence}
        missing = sorted(set(course['prerequisite_codes']) - set(passed_courses or []))
        return {'status': 'partially_answered', 'answer': base + m((' لم يتحقق شرط المتطلبات السابقة في الملف الافتراضي: ' + '، '.join(missing)
            if missing else ' تحقق شرط المتطلبات السابقة في الملف الافتراضي.'),(' Missing prerequisites in the fictional example: '+', '.join(missing) if missing else ' The prerequisite condition is satisfied in the fictional example.')) + m(' هذه نتيجة فحص المتطلبات فقط؛ أهلية التسجيل الكاملة تتطلب اللوائح والموافقات الأخرى.',' This checks prerequisites only. Full registration eligibility also depends on other regulations and approvals.'),
            'prerequisites_satisfied': not missing, 'missing': missing, 'evidence': evidence}
    return None

def evaluate_registration(question, evidence,language='ar'):
    def m(ar,en):return choose(ar,en,language)
    q = normalize(question)
    if not ('معدل' in q and any(k in q for k in ['ساع', 'اسجل', 'تسجيل'])):
        return None
    gpa = re.search(r'معدل(?:ي)?\s*(?:هو|يساوي)?\s*([\d.]+)', q)
    if not gpa:
        return {'status': 'needs_clarification', 'answer': m('ما المعدل الافتراضي بالأرقام؟','What is the fictional GPA as a number?'), 'evidence': []}
    try:
        value = float(gpa.group(1))
    except ValueError:
        return {'status': 'needs_clarification', 'answer': m('اكتب المعدل الافتراضي كرقم صالح مثل 2.8.','Enter a valid fictional GPA, such as 2.8.'), 'evidence': []}
    if not 0 <= value <= 4:
        return {'status': 'needs_clarification', 'answer': m('الجدول التجريبي يستخدم مقياس 0 إلى 4؛ حدد المقياس المناسب لوثيقتك.','The fictional table uses a 0–4 GPA scale. Specify the scale used by your document.'), 'evidence': []}
    matched = [r for r in evidence if r.get('registration_rule') and
        r['registration_rule']['gpa_min'] <= value < r['registration_rule']['gpa_max']]
    if not matched:
        return None
    conditions = {(r['registration_rule']['min_credits'], r['registration_rule']['max_credits'], r['registration_rule']['conditions']) for r in matched}
    if len(conditions) > 1:
        return {'status': 'needs_clarification', 'answer': m('توجد قواعد تسجيل مختلفة؛ حدد نسخة اللائحة والبرنامج.','Conflicting registration rules are available. Specify the regulation version and program.'), 'evidence': matched}
    rule = matched[0]['registration_rule']
    return {'status': 'partially_answered', 'answer': m(f"حسب صف المعدل {value:g}: الحد الأدنى {rule['min_credits']:g} والأقصى {rule['max_credits']:g} ساعة. الشروط: {rule['conditions']}. لا يثبت هذا وحده أهلية التسجيل؛ يجب التحقق من جميع الشروط.",f"For GPA {value:g}, the table lists a minimum of {rule['min_credits']:g} and a maximum of {rule['max_credits']:g} credit hours. The source conditions must also be reviewed; this does not establish full registration eligibility."), 'evidence': matched[:1]}
