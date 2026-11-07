# Architecture and evidence contract

User question → privacy/scope guards → resolve follow-up from user questions → corpus/program/version/document filter → local E5 cosine + BM25 + structured course/GPA signals → RRF → duplicate removal → evidence.

Evidence → deterministic credit/prerequisite/registration-table logic where supported; otherwise evidence-bound Gemini JSON → verify evidence IDs and source numbers → attach citation metadata from SQLite → Arabic RTL answer with source cards.

## Modules

| Module | Responsibility | External calls |
|---|---|---|
| `rag/ingestion.py` | PDF/TXT/DOCX, intact articles and exceptions, row/header chunks, source metadata | None |
| `rag/text.py` | Separate Unicode/Arabic/numeral normalization; course-code extraction, modest colloquial query expansion | None |
| `rag/store.py` | SQLite transactions, documents, chunks, minimal usage | None |
| `rag/retrieval.py` | Local E5, vector cache, BM25, RRF, exact codes/numeric range, filters | None at runtime |
| `academic/rules.py` | Prerequisite graph, missing data, scoped course match, explicit credit tables | None |
| `providers/gemini.py` | Verified model only, structured generation, bounded retries/concurrency and usage | Google Gemini API |
| `rag/service.py` | Answerability, version clarification, deterministic/provider routing, safe citations | Through provider only |
| `app.py` | Local web API, upload constraints, original-source routes | None directly |
| `evaluation/run.py` | Draft relevance labels, actual local measurements, explicit no-LLM evaluation | None |

## Persistence

`data/academia.sqlite`: documents, original chunks, separate normalized text and metadata JSON; usage stores model/status/token metadata only. Uploads use server-generated filenames. Original titles are display data and escaped. `vectors.npy` and `vector_ids.json` cache embeddings in stable chunk order. `embedding_model.json` records the exact model revision and local snapshot. Provider verification binds the configured model to a local key fingerprint; no key is stored in the report.

Chunk metadata: stable evidence ID, document ID, source title, original excerpt, PDF page (nullable), text unit, printed label (nullable), page range, article (nullable), source version/program/effective date, extracted course identifiers, credits and prerequisites when unambiguous. The original file remains available. TXT/DOCX do not have reliable PDF pagination.

## Trust and limits

Document text is prompt data and is never executed. The system prompt is independent of documents. Model claims must cite provided IDs; citation pages/versions are never accepted from the model. Claim numeric tokens must occur in cited excerpts. These checks establish location and numeric consistency, not full semantic grounding. Humans review negation, exceptions, and claim support.

The initial delivery used fictional fixtures. The current application indexes the supplied Hebron public-document corpus and retains fixtures only in their explicit synthetic scope. Automatic retrieval switches entirely to genuine documents when any are ready, preventing fictional policy leakage into real-document answers. A specific plan/version must be chosen when applicable versions conflict. Upload order is not applicability.

This single-process prototype uses one model on CPU, an ingestion mutex, a retrieval lock, and one concurrent Gemini call. Run one server worker. API attempts are counted against a small local daily limit (UTC); retries are at most two total attempts and only for 5xx. Timeout and quota errors return true evidence as diagnostics, never simulated generation.

## Hebron extension

The existing SQLite database is migrated additively with programs, study_plans, courses, plan_courses, prerequisite_rules, academic_forms, source_references and review_queue. Plan-course observations retain source-specific credit/requirement/elective/prerequisite data. Source titles, years, totals and representative values are bound to reviewed file hashes. Geometry-based extraction accommodates both real column layouts; raw cells and unverified rows remain inspectable. No cross-plan repair or merging occurs.

The router reads reviewed plan totals and course fields directly from SQLite, resolves forms from the catalog, routes missing regulation questions to insufficient evidence, and isolates conduct retrieval. Gemini remains independent and handles sufficiently evidenced narrative questions. A selected plan's exact source reference is an additional weighted RRF signal for plan-total questions.
