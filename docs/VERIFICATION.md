# Verification record — 7 November 2026

## Actual environment

Windows, CPython 3.12.16, fresh project-specific `.venv`. All 85 installed distributions passed the dependency compatibility check (`uv pip check`). Direct installed versions are pinned in `requirements.txt`; the full inspection environment is recorded in `requirements-lock.txt`.

## Actual test results

- **54/54 pytest cases passed** after the final code changes. Isolated database; no real student records; Gemini network generation disabled in tests.
- **15/15 offline evaluation cases passed** on the two actually indexed fictional documents (19 chunks, six parsed courses). Local multilingual embeddings + BM25 + RRF enabled. Latest machine-readable results: `data/evaluation_results.json`; human-readable results: `data/evaluation_results.md`.
- **Provisional Hit@5 = 1.000; Precision@5 = 0.254545** over 11 cases with nonempty draft relevance sets. Fixed denominator 5. Low draft Precision@5 reflects sparse, incomplete relevance labels and extra retrieved passages; it is not a claim of high precision. References require Student 3's actual review before use as a formal benchmark.
- **0 citation-location failures** in the offline evaluation. This checks stored IDs, excerpt text and PDF-page metadata; it does not prove semantic entailment or complete generated-claim grounding.

Pytest covers normalization/negation/numbers, exception-preserving articles and page continuations, PDF labels and page extraction, scan refusal, DOCX table headers, guarded OR prerequisites, actual course credits, prerequisite chains/missing data, version and same-version conflicts, filters, follow-ups, malformed GPA, refusals, upload/signature/declaration controls, cross-origin blocking, original-source links, privacy declarations, request bounds, bounded retries, 429/403/invalid-key/model errors, timeout sanitization, concurrency, daily cap, invented citations/numbers, context budget and model-revision vector-cache invalidation.

## Real Gemini verification

The user confirmed the supplied API project is Free tier. The app independently inspected current official model and pricing documentation, listed available models using the official `google-genai` SDK, and made a real minimal request:

- Requested and returned model: **`gemini-3.5-flash-lite`**.
- Minimal response: `OK`.
- Real returned usage: 8 input tokens, 2 output tokens, 10 total.
- Configured the exact model in local `.env`; key never printed, returned to the browser, or packaged.
- No billing change and no paid-only model fallback. The API cannot independently attest the owner's billing-account state; Free-tier confirmation comes from the user.

Browser-verified end-to-end generation on the actual indexed fictional corpus:

| Question | Observed response / evidence | Actual total tokens |
|---|---|---:|
| Minimum attendance | 80% from fictional article 1; exact clickable excerpt; fictional warning | 1,250 |
| Colloquial excessive absence | Over-20% consequence plus medical-committee exception and no automatic exemption; fictional article 1 | 1,287 |
| CS102 prerequisite and withdrawal conditions | CS101 requirement from the plan plus fictional article 2 withdrawal conditions, with both documents cited | 1,131 |

These are real model responses, not canned answers. Their evidence was inspected by the AI during this task; **human claim-by-claim sign-off remains pending**. Screenshots are saved locally under `output/` when captured and excluded from the source archive.

## Browser and HTTP verification

Viewed the Arabic RTL dashboard, chat, plan explorer, evaluation controls and prerequisite check in the browser. The fictional passed-code check correctly reports prerequisite-only satisfaction, with a warning that it is not full registration eligibility. The evaluation button invokes the real local runner. Tested the mobile breakpoint at 390×844; document width did not overflow (client and scroll width both 375 excluding scrollbar). Original-source pages are exercised through API integration tests and final HTTP smoke checks.

`python -m scripts.smoke_local` passed **6/6** checks against the running server via actual HTTP: retrieval, course credits, GPA row and numeric follow-up, unsupported exam date, out-of-scope request, and all returned source-view links. The API attempt counter did not change. Results: `data/smoke_results.json`.

## Failures found and corrected

- Isolated version-conflict evaluation originally changed shared row state without its matching vector/BM25 state. Replaced with an isolated domain fixture; production index never changes for this test.
- Numeric GPA follow-up could fall back to generation instead of selecting a source table row. Added exact source-derived numeric range retrieval and explicit offline evaluation enforcement.
- Normalization maps Arabic final yaa forms consistently; updated exam-date guard to use the normalized form.
- Invented numeric tokens, uncited free-form model prose and nonexistent citation IDs are rejected or removed before display.

## Remaining external work

The **genuine university document pack has not arrived**. Only clearly labeled fictional documents are loaded, and the organizer guide is excluded. Student 3 must review genuine source tables/metadata, replace or verify reference cases, and sign off on claim grounding. Final business facts and the ≤12-slide PDF/PPTX presentation are also Student 3's responsibility; fillable documents are supplied.

Not claimed: production deployment, authenticated institutional service, complete OCR, universal table parsing, complete graduation eligibility, perfect semantic grounding, verified market statistics, or a human-reviewed benchmark. No code was pushed to GitHub.
