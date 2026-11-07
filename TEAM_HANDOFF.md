# Three-student handoff

## Current boundaries

| Owner | Files | Stable responsibility |
|---|---|---|
| Student 1 | `rag/`, `providers/`, `academic/`, `evaluation/`, `tests/` | Retrieval quality, official Gemini SDK, deterministic rules, evaluation |
| Student 2 | `app.py`, `templates/`, `static/`, launch/setup, README | Arabic UI, API integration, upload/source browsing, error display |
| Student 3 | genuine document review, `evaluation/cases.json`, `docs/BUSINESS_PLAN.md`, `docs/PRESENTATION_OUTLINE.md` | Evidence review, source relevance labels, business assumptions, final ≤12-slide presentation |

Agree on changes before editing a teammate's owned files. No prior project has been reused. The owner authorized publication to https://github.com/abu-shab/education. Never publish .env or runtime databases.

## API contracts

Interactive API specification: `/docs` while the local server is running.

- `GET /api/status`: real document count, chunk count, actual semantic mode, verified provider model, API attempt count.
- `GET /api/documents`: display metadata, `synthetic`, `status`, chunk count. Never server filenames/paths.
- `POST /api/documents`: multipart `file,title,version,program,effective_date,kind,synthetic,public_confirmed`. Supported kinds: regulations, plan, handbook, exams, schedule. Returns `{id,chunks,status}`.
- `POST /api/documents/{id}/reindex`; `DELETE /api/documents/{id}`; `GET /api/documents/{id}/file`.
- `POST /api/chat`: `{question, mode:"generate"|"retrieve", history:[previous USER questions], program?, version?, document_id?, corpus:"auto"|"synthetic"|"real"}`. Only six prior questions, each ≤1500 characters.
- Chat response: `{status,answer,origin,resolved_question,claims,citations,synthetic,usage?,error_code?}`. `origin`: gemini, deterministic, retrieval_only, guardrail. Never label retrieval-only responses as Gemini output.
- Status: answered, partially_answered, needs_clarification, insufficient_evidence, out_of_scope, service_unavailable; diagnostic mode additionally returns retrieved.
- Citation: `{id,document_id,document,pdf_page?,page,page_end?,printed_page?,article?,version,program,synthetic,excerpt,url}`. Source viewer: `/sources/{id}`.
- `GET /api/courses`: parsed row plus source reference, program and version.
- `POST /api/prerequisites`: `{course_code,program,version,passed_courses:[fictional passed codes],corpus}`. Omit passed_courses to ask for missing information; empty array means none passed. Result is prerequisite-only, never final registration eligibility.
- `GET /api/evaluation`; `POST /api/evaluation/run`: local suite, zero model calls, real JSON/Markdown results.

## Student 3: critical next task

The supplied Hebron dataset is integrated: seven separate IT plans, twelve forms and conduct; three originals are retained but excluded. Current academic regulations are still missing. Review the 705 unverified plan-course rows and extracted names. The 25 visually checked rows record AI comparison, not human approval. Preserve the actual 61101 credit conflict and unknown prerequisite notation. See DATA_INGESTION_REPORT.md.

Review the 15 draft cases against their indexed fictional evidence now, or replace all references with genuine-document evidence after upload. Record `human_verified`, `reviewed_by`, and a review date only after actually checking each expected answer and relevance judgment. Add a claim-by-claim review of at least three real Gemini responses. Never rename draft evaluation figures as human-verified results.

Finalize the fillable business plan and nine official presentation topics. All numeric market claims need a source or an explicit assumption label. Submission is **before 15:00 Asia/Hebron on 7 November 2026**. Leave time for rehearsal and packaging; final slides are Student 3's responsibility.

## Demo in roughly three minutes

1. Show fictional-data warning and two source documents.
2. Attendance question → real Gemini answer → open its exact evidence.
3. Colloquial absence question → verify exception is preserved.
4. Advanced programming credit hours → deterministic table value.
5. CS102 prerequisite check → missing fictional details → passed-code check.
6. GPA 2.1 → follow-up 2.8 → updated source row; vague “higher” → clarification.
7. Next week's exam date → insufficient evidence; poem → out of scope.
8. Evaluation dashboard → actual results and pending human review.

See `docs/VERIFICATION.md` for the recorded test outcomes. Rehearse with few Gemini calls; retrieval and prerequisite checks use no API quota.

## Hebron integration handoff

Student 1: academic/pdf_tables.py, academic/structured.py, academic/hebron_catalog.py, scripts/import_hebron.py and evaluation/hebron.py extend the existing pipeline. No app rebuild or starter reuse. Student 2: existing chat/library/plan UI now shows review status and includes searchable form discovery and a separate conduct scope. Student 3: review source hashes and pending items at /api/review-queue, record reviewed names/rows in the source review observations only after visual comparison, and validate the current academic regulations when supplied.

The importer creates a local SQLite backup and preserves all original PDFs under data/originals. Source manifest: docs/HEBRON_SOURCE_MANIFEST.json. Evidence IDs remain stable for unchanged inputs. Data categories and review states are relational, and unreviewed data do not drive authoritative course answers. Final source-based evaluation remains provisional pending human sign-off.

Chat privacy is a persistent non-blocking reminder. No checkbox or confirmation field is required by /api/chat; identifier guards remain active.

Reply language is server-detected from the latest question (code-only follow-ups inherit the prior question language). The chat response includes language=en/ar. Preserve original source metadata/excerpts, and use the response language for answer status, explanatory prose and reading direction. Gemini receives a trusted language directive and Arabic claims are rejected for English requests.
