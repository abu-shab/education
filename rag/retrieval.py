import json
import os
import re
import threading
import numpy as np
from rank_bm25 import BM25Okapi
from config import DATA
from rag import store
from rag.text import tokens, codes, expand_query, normalize

class Retriever:
    def __init__(self):
        self.lock = threading.RLock()
        self.model = None
        self.embedding_info = {}
        self.embedding_status = 'not initialized'
        self.rows = []
        self.vectors = None

    def load_model(self):
        if self.model is not None:
            return True
        manifest = DATA / 'embedding_model.json'
        if not manifest.exists():
            self.embedding_status = 'BM25 only: run python -m scripts.prepare_embeddings'
            return False
        try:
            from sentence_transformers import SentenceTransformer
            info = json.loads(manifest.read_text(encoding='utf-8'))
            self.embedding_info = {k:info[k] for k in ('model','revision')}
            self.model = SentenceTransformer(info['local_path'], device='cpu', local_files_only=True)
            self.embedding_status = f"{info['model']} @ {info['revision']} (CPU)"
            return True
        except Exception:
            self.embedding_status = 'Local embedding model unavailable; BM25 diagnostic remains available'
            return False

    def refresh(self):
        with self.lock:
            self.rows = store.chunks()
            self.vectors = None
            self.lexical = BM25Okapi([tokens(r['text']) or ['_'] for r in self.rows]) if self.rows else None
            if not self.rows or not self.load_model():
                return
            ids = [r['id'] for r in self.rows]
            cache = DATA / 'vector_ids.json'
            vector_path = DATA / 'vectors.npy'
            fingerprint = {'embedding':self.embedding_info, 'chunks':[r['id'] + ':' + r['normalized'] for r in self.rows]}
            if cache.exists() and vector_path.exists() and json.loads(cache.read_text(encoding='utf-8')) == fingerprint:
                self.vectors = np.load(vector_path, allow_pickle=False)
            else:
                try:
                    self.vectors = self.model.encode(['passage: ' + r['text'] for r in self.rows],
                        normalize_embeddings=True, batch_size=16, show_progress_bar=False)
                    np.save(vector_path, self.vectors)
                    cache.write_text(json.dumps(fingerprint, ensure_ascii=False), encoding='utf-8')
                except Exception:
                    self.vectors = None
                    self.embedding_status = 'Embedding indexing failed; BM25 diagnostic available'

    def search(self, question, *, limit=5, document_id=None, program=None, version=None, corpus='auto', scope='academic', kinds=None, plan_id=None):
        with self.lock:
            rows = self.rows
            if not rows:
                return []
            real = any(not r['synthetic'] for r in rows)
            plan_anchor=None
            if real and corpus!='synthetic' and scope=='academic' and re.search(r'total|اجمالي|خطه|study.?plan',normalize(question)):
                from academic.structured import selected_plans
                selected=selected_plans(question,plan_id=plan_id,program=program,version=version,document_id=document_id)
                if len(selected)==1:
                    plan_id=selected[0]['id']
                    with store.connect() as db:
                        reference=db.execute('SELECT chunk_id FROM source_references WHERE id=?',
                            (selected[0]['total_credits_reference'],)).fetchone()
                    plan_anchor=reference['chunk_id'] if reference else None
            pool = [i for i, r in enumerate(rows)
                if (not document_id or r['document_id'] == document_id)
                and (not program or r['program'] == program)
                and (not version or r['version'] == version)
                and (not plan_id or r.get('academic_plan_id')==plan_id)
                and (not kinds or r['kind'] in kinds)
                and (scope=='all' or (r['kind']=='conduct' if scope=='conduct' else r['kind']=='form' if scope=='forms' else r['kind']!='conduct'))
                and (corpus == 'all' or (r['synthetic'] if corpus == 'synthetic' or (corpus == 'auto' and not real) else not r['synthetic']))]
            if not pool:
                return []
            q = expand_query(question)
            lexical = self.lexical.get_scores(tokens(q))
            ranks = [sorted(pool, key=lambda i: lexical[i], reverse=True)]
            anchor=[i for i in pool if rows[i]['id']==plan_anchor] if plan_anchor else []
            semantic = None
            if self.vectors is not None:
                v = self.model.encode(['query: ' + question], normalize_embeddings=True, show_progress_bar=False)[0]
                semantic = self.vectors @ v
                ranks.append(sorted(pool, key=lambda i: semantic[i], reverse=True))
            exact = set(codes(question))
            if exact:
                ranks.append(sorted([i for i in pool if exact.intersection(rows[i].get('course_codes', []))],
                    key=lambda i: (rows[i].get('course',{}).get('code') in exact, len(exact.intersection(rows[i].get('course_codes', [])))), reverse=True))
            gpa = re.search(r'معدل(?:ي)?\s*(?:هو|يساوي)?\s*([\d.]+)', normalize(question))
            structured = set()
            if gpa:
                try:
                    value = float(gpa.group(1))
                    structured = {i for i in pool if rows[i].get('registration_rule') and
                        rows[i]['registration_rule']['gpa_min'] <= value < rows[i]['registration_rule']['gpa_max']}
                except ValueError:
                    pass
            if structured:
                ranks.append(sorted(structured))
            if anchor:
                # A source reference resolved from the selected relational plan
                # is a strong, exact metadata signal; it is not a generated passage.
                ranks.append(anchor)
            scores = {}
            for ranking in ranks:
                for rank, i in enumerate(ranking[:40]):
                    scores[i] = scores.get(i, 0) + (2 if ranking is anchor else 1) / (60 + rank + 1)
            result, seen = [], set()
            for i in sorted(scores, key=scores.get, reverse=True):
                r = rows[i]
                # RRF is ranking, not confidence. Exclude unrelated lexical/semantic candidates.
                has_exact = bool(exact.intersection(r.get('course_codes', [])))
                if lexical[i] <= 0 and not has_exact and i not in structured and i not in anchor and (semantic is None or semantic[i] < .76):
                    continue
                key = (r['document_id'], r['normalized'])
                if key in seen:
                    continue
                seen.add(key)
                result.append({**r, 'score': round(scores[i], 6), 'lexical_score': round(float(lexical[i]), 4),
                    'semantic_score': round(float(semantic[i]), 4) if semantic is not None else None})
                if len(result) == limit:
                    break
            return result

retriever = Retriever()
