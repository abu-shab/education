# Hebron University data ingestion report

Generated: 2026-11-07T10:53:57.009133+00:00

23 supplied PDFs found; 23/23 preserved originals match their manifest SHA256. No source PDF was modified.
20 included: 7 IT plans, 12 procedural forms, 1 conduct code. Three retained originals are excluded from the default IT corpus.
730 plan-course observations stored: 25 visually checked code/hour/prerequisite rows; 705 unverified rows. Names and unreviewed fields remain candidate extraction, not verified academic facts.
712 pending review items. 53 nonempty genuine PDF pages indexed into 847 chunks; the seventh page of the 2026 SE-minor PDF is blank. Demo fixtures remain stored but are excluded from automatic real-data answers.
Visual comparisons were performed by Codex AI against rendered supplied pages. This is not institutional or human sign-off. Source observations are bound to reviewed SHA256 values.

## Files and actual results

| Source file | Classification / status | PDF pages | Checked / unverified course rows | Indexed pages / chunks | Extraction |
|---|---|---:|---:|---:|---|
| 014-form.pdf | form / included | 1 | 0 / 0 | 1 / 3 | success |
| 015-form.pdf | form / included | 1 | 0 / 0 | 1 / 2 | success |
| 016-form.pdf | form / included | 1 | 0 / 0 | 1 / 2 | success |
| 017-form.pdf | form / included | 1 | 0 / 0 | 1 / 2 | success |
| 018-form.pdf | form / included | 1 | 0 / 0 | 1 / 2 | success |
| 019-form.pdf | graduate_language_review_form / excluded | 1 | 0 / 0 | 0 / 0 | inspected_not_indexed |
| 020-form.pdf | form / included | 1 | 0 / 0 | 1 / 3 | success |
| 021-form.pdf | form / included | 1 | 0 / 0 | 1 / 3 | success |
| 022-form.pdf | form / included | 1 | 0 / 0 | 1 / 2 | success |
| 023-form.pdf | form / included | 1 | 0 / 0 | 1 / 2 | success |
| 024-form.pdf | form / included | 1 | 0 / 0 | 1 / 2 | success |
| 027-form.pdf | form / included | 1 | 0 / 0 | 1 / 3 | success |
| 031-form.pdf | form / included | 1 | 0 / 0 | 1 / 2 | success |
| 032-form.pdf | medical_annual_deferral_form / excluded | 1 | 0 / 0 | 0 / 0 | inspected_not_indexed |
| Academic-Advisory-General Division.pdf | law_advisory_plan / excluded | 4 | 0 / 0 | 0 / 0 | inspected_not_indexed |
| conduct.pdf | conduct / included | 11 | 0 / 0 | 11 / 30 | success |
| بكالوريوس الأمن السيبراني 2022.pdf | plan / included | 4 | 3 / 96 | 4 / 108 | success |
| بكالوريوس الأمن السيبراني- مسار جرائم الكترونية 2022.pdf | plan / included | 4 | 3 / 81 | 4 / 91 | success |
| بكالوريوس تكنولوجيا الويب والوسائط المتعددة 2022.pdf | plan / included | 4 | 3 / 98 | 4 / 109 | success |
| بكالوريوس رئيسي علم الحاسوب- فرعي ادارة الاعمال 2022.pdf | plan / included | 4 | 3 / 109 | 4 / 120 | success |
| بكالوريوس رئيسي علم حاسوب – فرعي هندسة برمجيات 2026.pdf | plan / included | 7 | 4 / 110 | 6 / 126 | success |
| بكالوريوس علم الحاسوب 2022.pdf | plan / included | 4 | 5 / 105 | 4 / 118 | success |
| تخصص رئيسي علم الحاسوب فرعي علم البيانات والذكاء الاصطناعي 2024.pdf | plan / included | 4 | 4 / 106 | 4 / 117 | success |

## Plans, kept separate

| Plan ID | Year | Stated total credits | Extracted observations | Checked core rows |
|---|---:|---:|---:|---:|
| hu-cs-2022 | 2022 | 135.0 | 110 | 5 |
| hu-cs-ai-2024 | 2024 | 138.0 | 110 | 4 |
| hu-cs-business-2022 | 2022 | 138.0 | 112 | 3 |
| hu-cs-se-2026 | 2026 | 138.0 | 114 | 4 |
| hu-cyber-2022 | 2022 | 133.0 | 99 | 3 |
| hu-cybercrime-2022 | 2022 | 134.0 | 84 | 3 |
| hu-web-2022 | 2022 | 135.0 | 101 | 3 |

The stated totals come from visually reviewed headings. They are never calculated by summing all elective offerings. Mandatory/elective classification comes from the actual enclosing headings, including cross-page continuation. Unknown or ambiguous prerequisite semantics remain unverified.

## Exclusions and warnings

- 019-form.pdf: Graduate-studies language review; outside the IT undergraduate MVP.
- 032-form.pdf: Medical-college annual deferral; outside the IT undergraduate MVP.
- Academic-Advisory-General Division.pdf: Faculty of Law advisory plan; outside the IT knowledge corpus.
- بكالوريوس الأمن السيبراني 2022.pdf: Source university-requirement heading is 24, mandatory heading 18, while the displayed seven mandatory rows sum to 19. Preserve the printed source and seek institutional clarification.
- بكالوريوس الأمن السيبراني 2022.pdf: Course 61101 is printed as 2 credits on PDF page 1 and 3 credits on PDF page 2. Do not choose one value or merge the two observations.
- بكالوريوس تكنولوجيا الويب والوسائط المتعددة 2022.pdf: Source page 1 university-requirement heading 28 differs from 19 + 6 listed subtotals.
- بكالوريوس علم الحاسوب 2022.pdf: Source page 1 labels university requirements 28 credits, while its mandatory/elective subtotals are 19 and 6. Do not repair or infer a reconciled total.
- Built-in table detection produced spurious split columns and missed grids. The adapter uses actual border geometry, preserves raw cells, and handles the standalone cybersecurity plan's reversed code/name column order. Suspicious values are queued, never repaired from another plan.
- Form numbers 020 and 031 appear reversed in some extracted text spans; catalog numbers/titles were read from the rendered originals. Forms establish existence/purpose only, not eligibility, current deadlines or approval rights.
- Blank prerequisites mean unknown, not automatically none. “+” and “/” are preserved without assuming concurrency, AND or OR. The actual 61101 source conflict returns clarification with both pages.
- Exact source URLs were not supplied or established. Manifest source_url values are null; hebron.edu is the user-identified source institution, not an invented per-file download URL.
- Source titles, plan/year and checked core values are available; the remaining 705 rows and extracted names require further review. This is not a fully approved degree-audit database.

## Missing regulations

**Current academic degree/registration/examination regulations were not supplied.** No current attendance percentage, maximum withdrawal period, registration load, warning threshold or graduation entitlement is inferred from plans, blank forms, conduct rules, or fictional data. These questions explicitly return insufficient evidence. Graduation readiness cannot be established without a fully reviewed applicable plan, all governing requirements and sufficient fictional completed-course information.

## Actual tests

- Automated regression/integration tests: 83 passed, 0 failed; exit code 0.
- Reviewed source-based demonstrations: 21/21 passed; 0 failed. This offline runner makes no Gemini calls.
- Actual retrieval Hit@5: 1.0000; Precision@5: 0.3500. Relevance judgments are AI-reviewed and provisional pending human sign-off.
- Citation-location failures: 0; excluded-document chunk leaks: 0; foreign-key errors: 0.
- Initial real-corpus run: 16/20 behavior checks passed. It exposed program/year text being mistaken for course codes, a missing English form-discovery phrase, and a previously unseen real printed credit conflict. Routing was corrected; the source conflict is retained and now evaluated as clarification, not silently resolved.
- Initial retrieval Hit@5 was 0.80; plan-title/year filtering and the exact stored source-reference signal improved it. No reference answer or source location was generated by Gemini.
- Actual HTTP demonstrations: 21/21 passed; original PDF routes/hash checks 23/23 passed; zero Gemini calls during HTTP checks: True.
- Live Gemini answer on conduct evidence: model gemini-3.5-flash-lite, 5 cited claims, 5661 actual total tokens. AI source review recorded; human sign-off remains pending. The browser form search and plan explorer also worked with no console errors.

## Reproduce / review

Run `python -m scripts.import_hebron`, `python -m evaluation.run`, and `python -m scripts.report_ingestion --test` from the existing Python 3.12 environment. The import is idempotent, backs up the live SQLite database, preserves original bytes, and touches only its own hu-* document records. A changed hash invalidates visual review. Missing expected inputs are reported in the manifest.
Review queue: GET /api/review-queue. Plans: /api/plans. Form search: /api/forms?q=... . Manifest: /api/source-manifest. Existing chat/source/library UI remains functional.
Full file manifest: docs/HEBRON_SOURCE_MANIFEST.json. Reviewed reference cases: evaluation/hebron_cases.json. Actual evaluation table: docs/HEBRON_EVALUATION_RESULTS.md.
