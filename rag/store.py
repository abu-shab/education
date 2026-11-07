import json
import sqlite3
from contextlib import contextmanager
from config import DATA

@contextmanager
def connect():
    db = sqlite3.connect(DATA / 'academia.sqlite', timeout=30)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init():
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS documents (
          id TEXT PRIMARY KEY, title TEXT NOT NULL, filename TEXT NOT NULL,
          version TEXT NOT NULL, program TEXT NOT NULL, effective_date TEXT,
          synthetic INTEGER NOT NULL, status TEXT NOT NULL, error TEXT,
          sha256 TEXT NOT NULL, kind TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS chunks (
          id TEXT PRIMARY KEY, document_id TEXT REFERENCES documents(id) ON DELETE CASCADE,
          text TEXT NOT NULL, normalized TEXT NOT NULL, metadata TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS usage (
          id INTEGER PRIMARY KEY, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          model TEXT, status TEXT, metadata TEXT
        );
        ''')
        existing={r['name'] for r in db.execute('PRAGMA table_info(documents)')}
        for name, declaration in {
            'original_filename':'TEXT', 'document_type':'TEXT', 'plan_year':'INTEGER',
            'source_url':'TEXT', 'pdf_page_count':'INTEGER',
            'inclusion_status':"TEXT NOT NULL DEFAULT 'included'",
            'review_status':"TEXT NOT NULL DEFAULT 'unreviewed'",
            'exclusion_reason':'TEXT'
        }.items():
            if name not in existing:db.execute(f'ALTER TABLE documents ADD COLUMN {name} {declaration}')
        db.executescript('''
        CREATE TABLE IF NOT EXISTS programs (
          id TEXT PRIMARY KEY, name_ar TEXT NOT NULL, name_en TEXT, institution TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS source_references (
          id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
          pdf_page INTEGER NOT NULL CHECK(pdf_page>=1), bbox TEXT, raw_excerpt TEXT NOT NULL,
          chunk_id TEXT REFERENCES chunks(id) ON DELETE SET NULL, review_status TEXT NOT NULL,
          review_method TEXT, reviewed_by TEXT
        );
        CREATE TABLE IF NOT EXISTS study_plans (
          id TEXT PRIMARY KEY, program_id TEXT NOT NULL REFERENCES programs(id),
          document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
          title TEXT NOT NULL, plan_year INTEGER NOT NULL, version TEXT NOT NULL,
          total_credits REAL, total_credits_reference TEXT REFERENCES source_references(id),
          review_status TEXT NOT NULL, extraction_status TEXT NOT NULL, warnings TEXT NOT NULL DEFAULT '[]'
        );
        CREATE TABLE IF NOT EXISTS courses (
          id TEXT PRIMARY KEY, code TEXT NOT NULL, code_key TEXT NOT NULL,
          name_ar TEXT, name_en TEXT
        );
        CREATE TABLE IF NOT EXISTS plan_courses (
          id TEXT PRIMARY KEY, plan_id TEXT NOT NULL REFERENCES study_plans(id) ON DELETE CASCADE,
          course_id TEXT NOT NULL REFERENCES courses(id), credit_hours REAL,
          requirement_category TEXT, mandatory INTEGER CHECK(mandatory IN (0,1) OR mandatory IS NULL),
          prerequisite_expression TEXT, source_reference_id TEXT NOT NULL REFERENCES source_references(id),
          review_status TEXT NOT NULL, verified_fields TEXT NOT NULL DEFAULT '[]', raw_extraction TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS prerequisite_rules (
          id TEXT PRIMARY KEY, plan_course_id TEXT NOT NULL REFERENCES plan_courses(id) ON DELETE CASCADE,
          expression TEXT, interpretation TEXT NOT NULL, prerequisite_codes TEXT NOT NULL,
          review_status TEXT NOT NULL, source_reference_id TEXT NOT NULL REFERENCES source_references(id)
        );
        CREATE TABLE IF NOT EXISTS academic_forms (
          id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
          form_number TEXT NOT NULL, official_title TEXT NOT NULL, intended_use TEXT NOT NULL,
          keywords TEXT NOT NULL, review_status TEXT NOT NULL,
          source_reference_id TEXT NOT NULL REFERENCES source_references(id)
        );
        CREATE TABLE IF NOT EXISTS review_queue (
          id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
          plan_course_id TEXT REFERENCES plan_courses(id) ON DELETE CASCADE,
          source_reference_id TEXT REFERENCES source_references(id), reason TEXT NOT NULL,
          raw_extraction TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', notes TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_plan_courses_plan ON plan_courses(plan_id);
        CREATE INDEX IF NOT EXISTS idx_courses_code ON courses(code_key);
        ''')

def documents():
    with connect() as db:
        return [dict(r) for r in db.execute('''SELECT d.*, (SELECT count(*) FROM chunks c WHERE c.document_id=d.id) chunk_count
            FROM documents d ORDER BY created_at DESC, title''')]

def chunks():
    with connect() as db:
        return [{**dict(r), **json.loads(r['metadata'])} for r in db.execute('''
            SELECT c.*, d.title, d.version, d.program, d.effective_date, d.synthetic, d.kind,
              d.review_status AS document_review_status, d.inclusion_status, d.source_url
            FROM chunks c JOIN documents d ON c.document_id=d.id WHERE d.status='ready' AND d.inclusion_status='included'
            ORDER BY c.id''')]

def usage(model, status, metadata=None):
    with connect() as db:
        db.execute('INSERT INTO usage(model,status,metadata) VALUES(?,?,?)',
                   (model, status, json.dumps(metadata or {}, ensure_ascii=False)))
