# ACADEMIA AI — Smart Academic Advisor

Freshly implemented for the IEEE RAG Hackathon at Bethlehem University, 7 November 2026. Arabic RTL academic-document assistant with local hybrid retrieval and evidence-bound Gemini generation.

**Current corpus: supplied Hebron University PDFs.** Seven separate IT plans, twelve procedural forms and the conduct code are integrated. Three out-of-scope originals are retained and excluded. There are 730 plan-course observations: 25 visually checked core rows and 705 unverified rows in the review workflow. Current academic regulations are missing. The original fictional fixtures remain explicitly labeled and excluded from automatic real-data answers. See [DATA_INGESTION_REPORT.md](DATA_INGESTION_REPORT.md).

## Start on this Windows computer

The project already has a working `.venv`, local embeddings, and the indexed Hebron sources with a relational academic database. A real minimal API call verified `gemini-3.5-flash-lite` on the supplied key. Launch from this folder:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000 --no-access-log
```

Open http://127.0.0.1:8000. First startup loads the local model and may take several seconds. Stop with Ctrl+C. If port 8000 is already running, use the existing window or change the port to 8001.

## Install on a clean Windows computer

Use Python **3.12** (tested: 3.12.16); do not use the machine's default Python 3.15 for this dependency set. `uv` is optional.

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
Copy-Item env.example .env
# Edit .env locally and set GEMINI_API_KEY. Never share or commit it.
.\.venv\Scripts\python.exe -m scripts.prepare_embeddings
# Put the 23 supplied PDFs under data/incoming, then import:
.\.venv\Scripts\python.exe -m scripts.import_hebron
# Only after confirming this key's API project says Free tier in AI Studio:
.\.venv\Scripts\python.exe -m scripts.verify_gemini --confirm-free-tier
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000 --no-access-log
```

Without uv: use `py -3.12 -m venv .venv`, then `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`. The clean machine must actually have Python 3.12 installed. The local model download needs internet once; after preparation all retrieval works offline. If preparation fails, the application truthfully reports BM25-only diagnostic mode. It never substitutes fake semantic vectors.

## What works

- Five functional views: dashboard, chat, plan explorer, document library, evaluation.
- PDF/TXT/DOCX extraction, preserved original text, separate normalized Arabic search text, section-aware chunks, table row plus header preservation.
- SQLite documents/chunks/usage, NumPy cosine similarity, BM25, reciprocal-rank fusion, course-code and numeric GPA-row matching, deduplication, program/version/document/corpus filters.
- Local `intfloat/multilingual-e5-small` embeddings with `query:` / `passage:` prefixes. Resolved revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`, 384 dimensions, CPU. No Gemini embedding calls or training/fine-tuning.
- Official `google-genai` SDK, structured answers, validated citation IDs, source-number checks, 18-second request timeout, one concurrent generation, five-second local spacing, default daily cap of 20 attempts (UTC), at most one retry for 5xx. No automatic retry of 429/daily quota, 403, invalid-key or unknown errors. SDK retries disabled.
- Clickable evidence cards and original-file links. PDF page and optional printed label are distinguished. TXT/DOCX use text units, never invented PDF pages. Citations are assembled by the server, not by Gemini.
- Deterministic course credit lookup, prerequisite chain and prerequisite-only checks. Satisfying prerequisites never becomes a full registration/graduation decision. Source-tagged GPA tables support partial credit-limit guidance with conditions.
- Follow-up question resolution reruns retrieval; it uses previous user questions, never previous model answers as evidence. Vague “higher GPA” asks for a number.
- Upload size/type/signature validation, DOCX expanded-size checks, public/synthetic declaration, local origin protection, escaped source text, no browser key, no question/transcript logging. Retrieval-only mode explicitly says no answer was generated.

## Review and refresh the supplied Hebron documents

1. Student 3 checks that documents are public and contain no personal records. Record program identity, plan version, effective date, and provenance.
2. Open **مكتبة المستندات**, upload each document with metadata, and leave the fictional checkbox **unchecked** for genuine public documents. The organizer guide is rejected.
3. Open retrieved excerpts and compare the original PDF pages and tables. Image-only scans need OCR and human checking outside this app. A successful extraction does not certify the contents.
4. The automatic corpus uses genuine documents exclusively as soon as any are ready; demo documents remain available only through the explicit fictional corpus selector. Check the plan explorer's labels too.
5. Review and replace `evaluation/cases.json` using actual indexed evidence IDs. Keep `human_verified=false` until a named reviewer has checked every reference answer and relevance judgment.
6. Re-run the evaluator and a few live grounded questions. Do not claim the fictional-corpus score represents university performance.

## Tests and evaluation

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m evaluation.run
```

Pytest uses an isolated database and disables network generation. When the Hebron plans are installed, the evaluator runs 21 source-based demonstrations against the actual documents; otherwise it retains the 15-case fictional fixture suite. Both modes make **zero Gemini calls**. The Hebron reference cases record AI visual review, not human or institutional sign-off. It saves `data/evaluation_results.json` and `.md`. Hit@5 averages whether at least one labeled relevant chunk appears in the first five. Precision@5 uses five as its fixed denominator. Metrics are provisional while human reference review is pending. Citation-location integrity is measured; semantic support of each generated claim requires separate human review.

See `DATA_INGESTION_REPORT.md` for current results and limits; `docs/VERIFICATION.md` records the earlier fictional-data milestone. The evaluation dashboard runs the same offline evaluator. It is intended for a trusted local team, not a public benchmark service.

## Gemini and zero additional billing

Google AI Pro does not establish API free access. The user confirmed the API project is Free tier; the app cannot infer or prove billing-account state from a successful text response. The verification script lists API models, checks current official free-tier pricing for the exact candidate, makes one minimal request, records returned usage/model metadata, and only then writes `GEMINI_MODEL` and the free-tier confirmation to local `.env`.

No billing account is enabled, no paid-only model is selected, and there is no automatic model failover. If project billing changes, **stop generation and recheck the project**: a free-eligible model name alone does not enforce a spending cap on a paid project. Set `GEMINI_FREE_TIER_CONFIRMED=false` to disable generation. Retrieving documents costs no Gemini quota. A verification on another key/model must be repeated. The daily application cap is a quota-saving control, not a cloud billing guarantee.

Official sources consulted 7 November 2026: [pricing](https://ai.google.dev/gemini-api/docs/pricing), [models](https://ai.google.dev/gemini-api/docs/models), [maintained SDK](https://ai.google.dev/gemini-api/docs/libraries), [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits). Exact project quotas vary; no unsupported requests-per-day entitlement is claimed.

## Known limits

- The supplied plans/forms/conduct are integrated; current academic registration/examination regulations are still missing. Only representative course fields have been visually checked. The remaining rows and extracted names require review.
- PDF extraction depends on text order and table detection. Arabic presentation forms are normalized only for search. Scans, complex merged cells, table continuations and unusual layouts require human review.
- Numbered articles are kept intact; long articles may exceed the chunk target. Oversized articles should be reviewed and split at meaningful sections with exceptions kept together. Embeddings have model token limits.
- Structured course extraction accepts explicit headers `code | name | credits | prerequisites` or `رمز المساق | اسم المساق | الساعات | المتطلبات السابقة`. Unrecognized tables remain searchable evidence; they do not become executable eligibility rules. OR, concurrent and minimum-grade conditions are not automatically reduced to simple prerequisites.
- Registration arithmetic recognizes explicit reviewed-style `gpa_min | gpa_max | min_credits | max_credits | conditions` tables. Boundaries are lower-inclusive, upper-exclusive. The provided fictional scale is 0–4. Other layouts stay evidence-only.
- Citation IDs and numeric validation reduce errors but do not prove semantic entailment. No production claim of perfect hallucination prevention is made.
- Privacy declarations and basic identifier detection are guardrails, not a de-identification guarantee. Never enter real student records or upload private documents. Only selected evidence and the resolved question go to Gemini; local embeddings and storage stay on this computer.
- No authentication/multi-tenant isolation. Keep the server bound to loopback. Do not publish it as a student-record system.

## Project structure and team

`rag/`: extraction, SQLite, retrieval, orchestration. `providers/gemini.py`: independent provider. `academic/rules.py`: deterministic academic logic. `app.py`: HTTP contracts. `templates/` and `static/`: fresh Arabic UI. `evaluation/`: references/runner. `tests/`: behavioral/integration/provider tests. `sample_data/`: fictional fixtures. See `TEAM_HANDOFF.md` and the fillable business/presentation documents.

## AI assistance disclosure and provenance

OpenAI Codex assisted in writing and debugging this new application, tests, synthetic fixtures, and draft documentation. No prior application, starter kit, template, or enterprise domain module was copied or reused. The original workspace contained only the organizer guide and video. All application/UI code was written for this task. Dependencies are third-party libraries listed in requirements; the pretrained embedding model comes from [intfloat/multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small). No new language model was trained or fine-tuned. Students must review and understand the implementation and finalize the reference review, business content and presentation.

GitHub repository: [abu-shab/education](https://github.com/abu-shab/education). Only source code, documentation and the supplied public source PDFs are published. Secrets, runtime databases, logs and model caches stay local.

## Hebron relational data and source routes

`documents`, `programs`, `study_plans`, `courses`, `plan_courses`, `prerequisite_rules`, `academic_forms`, `source_references`, and `review_queue` are stored in the existing SQLite database. Courses are scoped to their source plan; credits, elective status and prerequisite expressions stay on plan-course records. Blank or ambiguous prerequisite notation is never reduced to a passed-course rule. The actual 61101 source conflict is retained.

`python -m scripts.import_hebron` backs up SQLite and idempotently imports the supplied files, preserving every original PDF and hash. `academic/hebron_review_hashes.json` binds visual observations to the reviewed bytes; missing/changed hashes invalidate review. Generic uploads remain RAG sources and do not automatically create approved structured academic facts.

Structured routing answers plan totals and reviewed code/hour/prerequisite questions; the form catalog identifies existing procedures. Policy questions require academic regulations. Conduct is a separate retrieval scope. Existing Gemini generation, local E5/BM25/RRF and exact citation routes remain available.

New read-only endpoints: `/api/plans`, `/api/forms?q=...`, `/api/review-queue`, `/api/source-manifest`. The existing source viewer opens the original PDF page. Excluded documents are visible in the library with an exclusion label, but never enter the retrieval index.

Reproduce current checks:

```powershell
.\.venv\Scripts\python.exe -m evaluation.run
.\.venv\Scripts\python.exe -m scripts.report_ingestion --test
```

The source PDFs under `data/incoming/` were supplied by the user as public Hebron University documents (hebron.edu) and are included so the index can be reproduced. The three out-of-scope PDFs are retained for provenance and excluded by the importer. Exact original download URLs are unknown and recorded as null; no per-file URL is invented. Review provenance, per-file extraction outcomes, missing regulations and current test results are in `DATA_INGESTION_REPORT.md` and `docs/HEBRON_SOURCE_MANIFEST.json`.
