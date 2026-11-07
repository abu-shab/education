# ACADEMIA AI — fillable business plan (Student 3)

Status: working document, **not validated market research**. All example figures below are planning assumptions, not observed sales, market size, or quoted vendor costs. Replace or validate before presentation.

## Problem and evidence

Students struggle to locate applicable rules across handbooks, plans and tables. Validate with a short anonymous survey; do not collect names, student IDs or grade records.

- Survey date / reviewer: [fill]
- Respondent count: [fill; actual only]
- Repeated questions / time spent finding answers: [fill]
- Source URL / citation / page: [fill]

## Users, buyer, institutions and segments

Student user: Arabic-speaking students seeking evidence-backed explanations. Institution users: advisors, registration staff and document owners. Buyer: university administration/IT/student affairs, not individual students.

Initial segments: Arabic-speaking universities with public PDF handbooks; departments maintaining versioned plans; colleges with repeated registration questions. Choose initial geography, number of institutions and readiness from verified sources.

| Market | Definition | Verified quantity | Source/date | Formula |
|---|---|---|---|---|
| TAM | All eligible institutions in chosen geography | [fill] | [fill] | institution count × annual contract value |
| SAM | Institutions reachable with Arabic/public-doc deployment | [fill] | [fill] | qualified count × annual contract value |
| SOM | Realistic 36-month acquisition capacity | [fill] | [fill] | achievable customers × annual contract value |

Do not insert unsupported population figures. Student count is a usage estimate; institution count drives the B2B revenue model.

## Value and revenue model

Proposed B2B annual university subscription, with an optional onboarding fee for document review and configuration. Pilot on public documents; demonstrate exact citations, applicable-version clarification, refusal and deterministic prerequisite checks. No access to private student records in the prototype.

**Assumption for discussion only:** subscription $120/institution/month; onboarding $200 one-time. Buyer interviews needed: [names of roles, no private contact details]. Willingness to pay evidence: [fill].

## Costs and free-tier distinction

Hackathon prototype: Gemini project confirmed Free tier by owner; exact working model `gemini-3.5-flash-lite`; local application imposes request limits. Current API spending target is $0. Google AI Pro is not API quota. Never promise unlimited free production service.

Future commercial scenario: institutional data handling, quotas, tenancy, legal terms, authentication, support and hosting require separate design and approval. **No paid billing is enabled by this prototype.**

| Item | Illustrative monthly assumption | Verification/action |
|---|---|---|
| Fixed hosting | $25 | obtain actual provider quote; currently local computer |
| Fixed operations/admin | $250 | validate staff time and rates |
| Support per institution | $30 | time study and service-level definition |
| Future API reserve per institution | $10 | hypothetical business budget, not actual charge or enabled billing |
| Sales/onboarding labor | [fill] | include acquisition cost, do not treat fee as pure profit |

For a future priced API scenario, monthly model cost = requests × ((input tokens × input price/million) + (output tokens including thinking × output price/million)). Use actual usage metadata and the current [official pricing](https://ai.google.dev/gemini-api/docs/pricing). Do not assume today's free quota supports all future students.

## Example 12–36 month forecast — ALL CUSTOMER COUNTS ARE ASSUMPTIONS

Subscription $120/month; variable support+API reserve $40/customer/month; fixed costs $275/month. Excludes tax, salaries beyond operations assumption, churn, sales cost and onboarding income. This is a sensitivity illustration, not an investment forecast.

| Month | Assumed customers | Monthly recurring revenue | Variable costs | Fixed costs | Monthly operating balance |
|---|---:|---:|---:|---:|---:|
| 12 | 3 | $360 | $120 | $275 | -$35 |
| 24 | 8 | $960 | $320 | $275 | $365 |
| 36 | 15 | $1,800 | $600 | $275 | $925 |

Break-even with these assumptions: ceiling($275 / ($120 - $40)) = **4 institutions**. Recalculate after including salaries, acquisition, hosting quotes, churn and procurement cycle. Annual cash flow: [fill monthly acquisition/churn schedule; do not multiply endpoint revenue as though earned all year].

## Acquisition and 90-day marketing plan

| Period | Target and channel | Work | Budget assumption | Measurable outcome |
|---|---|---|---|---|
| Days 1–30 | Advisors/registration leaders; university introductions | 10 assumed discovery interviews; public-doc prototype | $100 assumption | validated recurring questions, 2 assumed pilot candidates |
| Days 31–60 | Department pilot and student ambassadors | supervised public-document trial; anonymous feedback | $150 assumption | citation-supported answers, refusal accuracy, measured time saved |
| Days 61–90 | University procurement/IT | pilot report, security/privacy review, paid-contract proposal | $250 assumption | 1 assumed signed pilot; actual conversion logged |

Track acquisition cost, activation, weekly active users, grounded-answer rate, unsupported-answer rate, source-click rate, advisor time saved, retention and institutional conversion. Define each denominator before reporting.

## Alternatives and differentiation

Alternatives to compare through actual interviews: manual advisor queues, handbook/PDF search, institutional FAQ/chatbots, and general document assistants. Do not claim competitor pricing/features without a dated primary source. Our proposed distinction: Arabic colloquial retrieval, exact source evidence, applicable-plan clarification, local embedding/storage and deterministic prerequisite checks. These benefits need user validation.

## Student 3 sign-off

Reviewed by/date: [fill]. Verified source list: [fill]. Replaced assumptions: [fill]. Remaining assumptions visibly labeled in slides: [fill]. No fabricated market statistics, sales, survey results, or human evaluations.
