# MUHAS DCEPD short-course system

Public site: https://muhas-dcepd.github.io/

This repository is the automation and public-publishing layer for the MUHAS Directorate of Continuing Education and Professional Development (DCEPD). REDCap remains the authoritative operational system.

- `/dcepd-courses/`: searchable public short-course catalogue and official application gateway.
- `/dcepd-dashboard/`: aggregate Project 75 course/run metrics and Project 79 application summaries.
- Historical workbook: dated snapshot under `dcepd-courses/downloads/`.

## System boundaries

**Project 75** is the authoritative short-course registry. It holds course identity, review/accreditation fields, Course Director contacts, vote code, course runs, public-catalogue state and Accreditation Publication Control (APC).

**Project 79** is the application and participant workflow. It holds applicant data plus the staff-only `participant_selection_certification` instrument for selection, batch assignment, attendance verification, GePG control number, fee verification and certification. That staff-only instrument must never be enabled as a public survey.

The public website is read-only. Applicant identities, contact fields, payment details and private management information are not published.

## GitHub Actions

### Daily refresh and deployment

Workflow: `.github/workflows/update-dcepd.yml`

Nominal schedule: **04:37 EAT daily** (`01:37 UTC`). GitHub scheduler timing is approximate.

The scheduled/manual full refresh:

1. exports Project 75 and Project 79;
2. checks the expected REDCap structure before any write;
3. updates only approved derived Project 75 record fields;
4. verifies writes;
5. rebuilds the public catalogue/dashboard and management outputs; and
6. deploys GitHub Pages.

Current structural baseline (4 October 2026):

- Project 75: **73 metadata fields**;
- Project 79: **73 metadata fields**;
- Project 79 forms: `short_course_application` and staff-only `participant_selection_certification`.

A failed full refresh stops downstream publication. The last successful deployment remains live.

### Accreditation Publication Control

Workflow: `.github/workflows/watch-accreditation.yml`

APC processes only explicit accreditation-letter requests entered in Project 75. Accreditation decisions, approval dates and approval references remain human-controlled. Historical valid reference numbers are never renumbered merely to remove gaps.

### Project 79 certificate listener

Workflow: `.github/workflows/watch-certificates.yml`  
Generator: `scripts/process_certificate_requests.py`

The listener processes only records that satisfy the approved certificate eligibility checks and have an explicit generation request. Its permitted Project 79 write-back is narrowly limited to certificate generation: upload `certificate_file`, set generated/date fields and clear the generation request after success.

Generated does not mean issued. Certificate issue remains a staff action.

The older duplicate Project 79 certificate pilot workflow/script was removed on 4 October 2026.

### Course Director Applicant Packs

Workflow: `.github/workflows/watch-project79-applicant-packs.yml`  
Generator: `scripts/process_project79_applicant_packs.py`

Nominal schedule: **05:15 EAT**, after the daily refresh.

The workflow is read-only against REDCap. It:

- loops only courses with Project 79 applications;
- uses the verified Project 75 Course Director email as the primary recipient;
- applies Course Director/contact QC before sending;
- creates `All Applicants`, `Selection Return` and `Cert-Graduands Return` worksheets;
- sends the first historic applicant pack per course, then full current-fiscal-year context;
- sends after 5 new applications, with a Friday catch-up for 1-4 new applications;
- stores per-course delivery state in `automation/applicant-pack-state.json`.

Returned workbooks are not auto-imported. A Coordinator/Admin saves the intended return sheet as **CSV UTF-8 (Comma delimited)** and imports it deliberately into Project 79.

Payment fields remain distinct:

- `payment_reference`: applicant-provided payment/reference information;
- `gepg_control_no`: official staff-recorded GePG control number, when available;
- `fee_verified`: staff verification/check of fee/payment status.

A GePG control number alone does not confirm payment.

## Safety rules

- Never write REDCap metadata/data dictionaries through the API.
- Do not expose the Project 79 staff-only instrument as a survey.
- Do not invent approval references, course codes, attendance, payments or certificate decisions.
- Do not turn missing/failed source data into false zero.
- Preserve historical course codes, accreditation references, Application IDs and certificate serials.
- Public catalogue/dashboard code remains read-only toward Project 79.
- Applicant-level packs are private and must only go to the verified Course Director and authorized DCEPD recipients.

## Required secrets

At minimum:

- `REDCAP_PROJECT75_TOKEN`
- `REDCAP_PROJECT79_TOKEN`

Email workflows additionally use the configured DCEPD SMTP secrets and `DCEPD_EMAIL_1` to `DCEPD_EMAIL_4`. Never store secret values in repository files or logs.

## Routine administration

Ordinary DCEPD users should work in REDCap, not GitHub. GitHub is for automation, audit and publishing.

For a failed workflow:

1. identify which workflow and step failed;
2. check whether the failure is technical or a REDCap/QC management exception;
3. do not modify REDCap structure as a workaround;
4. preserve the last verified state and rerun only after the cause is understood.

## Development

Python 3.12 is used for the public refresh, APC support, certificate listener and Applicant Pack components. The Project 75 verified refresh runtime uses R.

Run public-site tests with:

```bash
python -m unittest discover -s tests -p 'test_dcepd*.py'
```

The public deployment stages an explicit allowlist only. No OpenAlex dependency exists in this repository.
