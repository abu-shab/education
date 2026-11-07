"""Preserve source text; only the separate search representation is normalized."""
import hashlib
import json
import re
import uuid
import zipfile
from pathlib import Path
import pymupdf
from docx import Document
from config import DATA, CHUNK_SIZE, CHUNK_OVERLAP
from rag import store
from rag.text import normalize, codes

SECTION = re.compile(r'(?m)^(?=(?:المادة|مادة|Article|Section|##)\s*[^\n]*)', re.I)

def extract(path: Path):
    suffix = path.suffix.lower()
    pages = []
    if suffix == '.pdf':
        with pymupdf.open(path) as doc:
            if doc.is_encrypted:
                raise ValueError('ملف PDF محمي. ارفع نسخة نصية غير محمية.')
            if len(doc) > 500:
                raise ValueError('الحد الأقصى 500 صفحة.')
            for i, page in enumerate(doc):
                text = page.get_text(sort=True)
                tables = []
                try:
                    for table in page.find_tables().tables:
                        rows = table.extract()
                        if not rows:
                            continue
                        header = ' | '.join(str(x or '') for x in rows[0])
                        tables.extend(header + '\n' + ' | '.join(str(x or '') for x in row) for row in rows[1:])
                except (AttributeError, ValueError, RuntimeError):
                    pass
                pages.append({'page': i+1, 'pdf_page': i+1, 'printed_page': page.get_label() or None,
                              'text': text, 'tables': tables})
    elif suffix == '.txt':
        text = path.read_text(encoding='utf-8-sig')
        pages = [{'page': i+1, 'pdf_page': None, 'printed_page': None, 'text': t, 'tables': []}
                 for i, t in enumerate(text.split('\f'))]
        for p in pages:
            header = None
            for line in p['text'].splitlines():
                if line.count('|') < 3:
                    header = None
                    continue
                if any(k in normalize(line) for k in ['رمز المساق', 'code', 'gpa_min']):
                    header = line
                elif header and not re.fullmatch(r'[|:\s-]+', line):
                    p['tables'].append(header + '\n' + line)
    elif suffix == '.docx':
        with zipfile.ZipFile(path) as z:
            if sum(x.file_size for x in z.infolist()) > 50 * 1024 * 1024:
                raise ValueError('حجم الملف بعد فك الضغط كبير جداً.')
        doc = Document(path)
        tables = []
        for t in doc.tables:
            rows = [[c.text for c in r.cells] for r in t.rows]
            if rows:
                tables.extend(' | '.join(rows[0]) + '\n' + ' | '.join(row) for row in rows[1:])
        pages = [{'page': 1, 'pdf_page': None, 'printed_page': None,
                  'text': '\n'.join(p.text for p in doc.paragraphs), 'tables': tables}]
    else:
        raise ValueError('الأنواع المتاحة PDF وTXT وDOCX.')
    if not any(p['text'].strip() or p['tables'] for p in pages):
        raise ValueError('لم يُستخرج نص. يحتاج الملف المصوّر إلى OCR ومراجعة بشرية أولاً.')
    return pages

def section_chunks(text: str):
    sections = [s.strip() for s in SECTION.split(text) if s.strip()]
    for s in sections:
        # An article and all its exceptions stay together, even if it exceeds target size.
        if re.match(r'^(المادة|مادة|Article|Section|##)', s, re.I):
            yield s
            continue
        paragraphs = re.split(r'\n\s*\n', s)
        buf = ''
        for p in paragraphs:
            if buf and len(buf) + len(p) > CHUNK_SIZE:
                yield buf
                # Overlap whole paragraphs; never cut a table row or condition mid-line.
                tail = buf.split('\n\n')[-1]
                buf = tail if len(tail) <= CHUNK_OVERLAP else ''
            buf = (buf + '\n\n' + p).strip()
        if buf:
            yield buf

def course_from_text(text):
    """Only unambiguous header-tagged tables. Unrecognized layouts stay evidence-only."""
    lines = [s.strip() for s in text.splitlines() if s.count('|') >= 3]
    if len(lines) != 2:
        return None
    header = [normalize(x.strip()) for x in lines[0].split('|')]
    aliases = {'code': ['code', 'رمز المساق'], 'name': ['name', 'اسم المساق'],
               'credits': ['credits', 'الساعات'], 'prerequisites': ['prerequisites', 'المتطلبات السابقة']}
    cols = {}
    for key, names in aliases.items():
        found = [i for i, h in enumerate(header) if h in names]
        if not found:
            return None
        cols[key] = found[0]
    row = [s.strip() for s in lines[-1].split('|')]
    if max(cols.values()) >= len(row):
        return None
    result = {k: row[i] for k, i in cols.items()}
    if not codes(result['code']) or not re.fullmatch(r'\d+(?:\.\d+)?', normalize(result['credits'])):
        return None
    raw_prereq = result['prerequisites']
    # OR/concurrent/minimum-grade requirements must be reviewed; do not reduce them to AND.
    simple = raw_prereq.strip() in ('لا يوجد', 'none', '-') or bool(re.fullmatch(r'[A-Za-z0-9,;\s+-]+', raw_prereq))
    if re.search(r'\b(?:or|concurrent|grade)\b', raw_prereq, re.I):
        simple = False
    return {**result, 'code': codes(result['code'])[0], 'credits': float(normalize(result['credits'])),
            'prerequisite_codes': codes(raw_prereq), 'simple_prerequisites': simple}

def registration_from_text(text):
    lines = [s.strip() for s in text.splitlines() if s.count('|') >= 3]
    if len(lines) != 2:
        return None
    header = [normalize(x.strip()) for x in lines[0].split('|')]
    keys = ['gpa_min', 'gpa_max', 'min_credits', 'max_credits', 'conditions']
    if header != keys:
        return None
    values = [x.strip() for x in lines[1].split('|')]
    if len(values) != 5:
        return None
    try:
        return {**dict(zip(keys[:4], map(float, values[:4]))), 'conditions': values[4]}
    except ValueError:
        return None

def make_chunks(pages, document_id):
    result = []
    pending = ''
    for page in pages:
        parts = list(section_chunks(page['text']))
        # A final numbered article may continue across a physical page boundary.
        for idx, text in enumerate(parts + page['tables']):
            article = re.search(r'(?:المادة|مادة|Article|Section)\s*[\(（]?([\w٠-٩.-]+)', text, re.I)
            meta = {k: page[k] for k in ('page', 'pdf_page', 'printed_page')}
            article_label = article.group(0) if article else None
            if idx >= len(parts):
                row = text.splitlines()[-1]
                pos = page['text'].find(row)
                if pos >= 0:
                    preceding = list(re.finditer(r'(?:المادة|مادة|Article|Section)\s*[\(（]?([\w٠-٩.-]+)', page['text'][:pos], re.I))
                    if preceding:
                        article_label = preceding[-1].group(0)
            meta.update({'article': article_label, 'course_codes': codes(text)})
            course = course_from_text(text)
            if course:
                meta['course'] = course
            registration = registration_from_text(text)
            if registration:
                meta['registration_rule'] = registration
            result.append({'id': f'{document_id}-p{page["page"]}-{idx}', 'text': text,
                           'normalized': normalize(text), 'metadata': meta})
    # Link page-spanning articles by carrying their complete evidence into one chunk.
    for i in range(len(result)-1, 0, -1):
        prev, curr = result[i-1], result[i]
        if (prev['metadata'].get('article') and not curr['metadata'].get('article')
                and curr['metadata']['page'] == prev['metadata']['page'] + 1
                and not curr['metadata'].get('course')):
            prev['text'] += '\n\n' + curr['text']
            prev['normalized'] = normalize(prev['text'])
            prev['metadata']['page_end'] = curr['metadata'].get('page_end', curr['metadata']['page'])
            result.pop(i)
    return result

def document_fields(pages):
    """Infer only explicitly labeled source fields; unknown dates stay unknown."""
    text = '\n'.join(p['text'] for p in pages[:3])
    values = {'detected_title': next((s.strip() for s in text.splitlines() if s.strip()), '')[:250]}
    patterns = {
        'version': r'(?mi)^\s*(?:الإصدار|إصدار|نسخة الخطة|Plan version|Regulation version|Version)\s*[:：]\s*([^\n]+)',
        'program': r'(?mi)^\s*(?:البرنامج|التخصص|Program)\s*[:：]\s*([^\n]+)',
        'effective_date': r'(?mi)^\s*(?:تاريخ السريان|نافذ من|Effective date)\s*[:：]\s*(\d{4}-\d{2}-\d{2})\b',
    }
    for key, pattern in patterns.items():
        found = re.search(pattern, text)
        if found:
            values[key] = found.group(1).strip()[:80]
    return values

def ingest(path: Path, *, title, version='', program='', effective_date='', synthetic=False, kind='regulations', doc_id=None):
    # Rules guide is deliberately excluded even if mistakenly uploaded as a handbook.
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    guide = list(Path(__file__).resolve().parents[1].glob('*Guide*Academic*pdf'))
    if any(hashlib.sha256(g.read_bytes()).hexdigest() == digest for g in guide):
        raise ValueError('هذا دليل المسابقة، وليس لائحة أكاديمية. لا يمكن فهرسته كمصدر للسياسات.')
    pages = extract(path)
    detected = document_fields(pages)
    version = version or detected.get('version', '')
    program = program or detected.get('program', '')
    effective_date = effective_date or detected.get('effective_date', '')
    prefix = normalize(' '.join(p['text'][:3000] for p in pages[:2]))
    if 'ieee rag hackathon' in prefix or 'دليل المشاركين' in prefix:
        raise ValueError('دليل المسابقة غير مسموح في قاعدة اللوائح الأكاديمية.')
    doc_id = doc_id or uuid.uuid4().hex[:16]
    items = make_chunks(pages, doc_id)
    for item in items:
        item['metadata']['source_document_fields'] = detected
    if not items:
        raise ValueError('لا توجد مقاطع قابلة للفهرسة.')
    with store.connect() as db:
        db.execute('''INSERT INTO documents(id,title,filename,version,program,effective_date,synthetic,status,sha256,kind)
            VALUES(?,?,?,?,?,?,?,'ready',?,?) ON CONFLICT(id) DO UPDATE SET status='ready', error=NULL''',
            (doc_id, title, path.name, version, program, effective_date, int(synthetic), digest, kind))
        db.execute('DELETE FROM chunks WHERE document_id=?', (doc_id,))
        db.executemany('INSERT INTO chunks VALUES(?,?,?,?,?)', [(c['id'], doc_id, c['text'], c['normalized'],
            json.dumps(c['metadata'], ensure_ascii=False)) for c in items])
    return doc_id, len(items)
