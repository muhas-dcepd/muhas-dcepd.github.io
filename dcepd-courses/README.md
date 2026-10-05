# DCEPD course catalogue

The public catalogue is a downstream read-only view of Project 75.

Only Project 75 master records whose `public_catalogue` label is Yes are included. The catalogue generator does not independently decide accreditation, dormancy or publication eligibility; those are derived upstream in Project 75. `public_catalogue` remains the sole visibility control.

## Current baseline — 6 October 2026

- Public catalogue: **86 courses**.
- Project 75 master-course registry: **195 courses**.
- A recorded SCEPD `accreditation_date` is the substantive accreditation event. The verified Project 75 refresh may then establish first accreditation, generate the immutable course code, update lifecycle/accreditation status and determine catalogue eligibility.
- APC `approval_date` and `approval_reference` belong to the later accreditation-letter/publication-control process and do not gate course-code generation.
- Never-run newly accredited courses may still be public when otherwise eligible.
- Dormant courses remain hidden according to the upstream Project 75 dormancy rule.

## Published fields and search

The catalogue publishes an explicit public schema only. It includes course identity and public-facing fields such as title, code, organisational unit, fee where known, CPD where verified, summary, duration, delivery mode, target audience, learning outcomes, certificate information and next-offered date.

Private contacts, applicant identities, payment information and management-only fields are never published.

Search supports:
- free-text matching across public course content;
- primary subject categories; and
- secondary subject discovery derived from strong public-course keywords.

Secondary-subject matching affects discovery only. It does not change `public_catalogue` eligibility.

## Application gateway

Every Apply button opens the official Project 79 general application survey. Applicants select the intended course there. Project 79 applicant data remain private; only approved aggregate counts/geography appear on the public dashboard.

## Refresh and failure behaviour

The scheduled full refresh runs at **04:37 EAT daily**. A manual full refresh can also be run from `.github/workflows/update-dcepd.yml` with API refresh enabled.

The workflow:
1. refreshes and verifies Project 75/79-derived state;
2. rebuilds this catalogue and the aggregate dashboard;
3. validates public-site tests and search metadata; and
4. deploys GitHub Pages.

If a full refresh fails, publication stops and the last verified deployed site remains live.

## Taxonomy

`scripts/dcepd_taxonomy.json` contains curated title-bound primary categories/tags. The generator also applies secondary subject matching for discovery. Original course names and historical codes remain intact except for deliberate display/editorial normalization.

## Safety

- The catalogue is read-only toward REDCap.
- It never writes Project 75 or Project 79.
- It never publishes raw registry exports or applicant-level information.
- Missing source values remain missing; they are not invented.
- `date_next_offered` is informational only and never overrides `public_catalogue`.

Run tests with:

```bash
python -m unittest discover -s tests -p 'test_dcepd*.py'
```
