# MUHAS DCEPD short-course system

Public site: https://muhas-dcepd.github.io/

This repository is the automation and public-publishing layer for the MUHAS Directorate of Continuing Education and Professional Development (DCEPD). REDCap remains the authoritative operational system.

- `/dcepd-courses/`: searchable public short-course catalogue and official application gateway.
- `/dcepd-dashboard/`: aggregate Project 75 course/run metrics and Project 79 application summaries.
- Historical workbook: dated snapshot under `dcepd-courses/downloads/`.

## Documentation

Use these documents together:

- **This `README.md`** — system overview, boundaries, workflows, safety rules and the current closeout baseline.
- **`automation/project75/TECHNICAL_USER_MANUAL.md`** — step-by-step operating manual for the technical administrator, including manual refresh, workflow triage, structural changes, secrets, recovery and routine checks.
- **`automation/project75/HANDOFF.md`** — institutional continuity, locked rules, historical baselines, recovery references and transfer-of-custodianship context.

For day-to-day technical operation, start with the **Technical User Manual**. For architectural or recovery decisions, also consult the **HANDOFF**.

## Closeout baseline — 8 October 2026

The Design Lock V1 implementation is closed for routine operation.

- The latest push-based refresh/deploy completed successfully on 8 October 2026.
- Project 75 contains **195** master courses; the public catalogue contains **86** listed courses.
- The refreshed dashboard read **320** Course Run Log instances and **993 valid operational applications from 1,012 Project 79 attempt records**.
- The catalogue is run-aware. A course can be listed without being open for application; an **Apply** button appears only when an eligible future run is explicitly open and within its application window. At closeout, no course is assumed open merely because it is listed.
- Project 79 generic entry fails closed: the catalogue-entry notice is shown when run context is absent, the required `catalogue_entry_guard` has no default and uses a Stop Action, and the survey completion text is neutral rather than falsely confirming an application.
- Valid catalogue deep links provide the Project 79 course choice, `applied_run_id`, and the course-level CV/certificate requirement flags.
- CAPTCHA is not exposed in the current MUHAS REDCap project settings and is therefore an administrator/server-level follow-up rather than a Design Lock dependency.
- Project 79 course-choice QC remains a manual metadata review control. The closeout run reported **29 QC items**; these are administration items to review, not silent metadata writes.
- `run_participants` is temporarily editable while legacy Course Run Log entries are completed. Blank means unknown. Restore the read-only/derived control after legacy run cleanup is closed.

This closeout does not freeze ordinary data administration. New runs, applications, reaccreditations and corrections continue under the locked rules below.

## Design Lock V1 — run-based public applications

From 8 October 2026, the public application architecture is run-aware:

- Project 75 remains the permanent course master; its `record_id` is never reused.
- Each delivery is identified by `record_id-redcap_repeat_instance` (for example `203-1`).
- The Course Run Log is the delivery almanac. A catalogue Apply button is generated only when a future run is explicitly **Open for applications** and its application window is active.
- The catalogue deep-link supplies the verified Project 79 course choice, `applied_run_id`, and course-level CV/certificate requirement flags. Project 79 choice values are never assumed to equal Project 75 record IDs.
- Courses without an open run remain visible but show that applications are not open.
- The general Project 79 survey URL remains a gateway: without run context it shows the catalogue-entry notice and links visitors back to the catalogue.
- `date_next_offered` displayed publicly is derived from the earliest eligible future run start date rather than treated as a manually curated catalogue date.
- Project 79 course choices remain a reviewed metadata control: new approvals and renamed course labels are QC items, not silent metadata writes.

## System boundaries

**Project 75** is the authoritative short-course registry. It holds course identity, review/accreditation fields, Course Director contacts, vote code, course runs, public-catalogue state and Accreditation Publication Control (APC).

**Project 79** is the application and participant workflow. It holds applicant data plus the staff-only `participant_selection_certification` instrument for selection, batch assignment, attendance verification, GePG control number, fee verification and certification. That staff-only instrument must never be enabled as a public survey.

The public website is read-only. Applicant identities, contact fields, payment details and private management information are not published.

## GitHub Actions

### Pipeline checkout — 6 October 2026

The live repository currently contains five workflows:

| Workflow | Trigger / schedule | Operational role |
|---|---|---|
| `.github/workflows/update-dcepd.yml` | push to `main`; manual dispatch; daily at **04:37 EAT** | verified Project 75/79 refresh when API refresh is enabled; public catalogue/dashboard build; management artifact; tests/SEO; GitHub Pages deployment |
| `.github/workflows/watch-accreditation.yml` | push to its maintained files; manual dispatch; **every 15 minutes** | explicit Project 75 APC accreditation-letter/reference transactions |
| `.github/workflows/watch-certificates.yml` | push to its maintained files; manual dispatch; **every 15 minutes** | explicit Project 79 certificate-generation requests |
| `.github/workflows/watch-project79-applicant-packs.yml` | push to its maintained files; manual dispatch; daily at **05:15 EAT** | read-only Course Director Applicant Packs; live email only when SMTP configuration is complete |
| `.github/workflows/one-time-project75-fee-cleanup.yml` | manual / workflow-file push only | retained audit/maintenance workflow; **not routine operation** |

The full verified REDCap sync runs only on the daily schedule or on manual dispatch with `refresh_api=true`. It reconstructs the checksum-verified V2.2.12 runtime, applies the V2.2.13 compatibility patch, runs the live Project 75/79 verification pipeline, uploads the technical audit, rebuilds the public outputs, builds the management packet and deploys Pages.

A normal push to `main` **does not run the R Project 75 sync**, but it does rebuild the public catalogue/dashboard directly from the Project 75/79 APIs, run public-site tests/SEO and deploy Pages. This is why documentation/code commits may be followed by an automated “Refresh public DCEPD catalogue and activity dashboard” commit when generated public files change.

A manual dispatch with `refresh_api=false` is effectively a publish/test path using the existing generated data; it does not perform the live REDCap refresh.

Current generated public snapshot checked on 8 October 2026:

- Project 75 registered master courses: **195**;
- public catalogue courses: **86**;
- Course Run Log instances read by the dashboard: **320**;
- Project 79: **993 valid operational applications from 1,012 attempt records**;
- catalogue source timestamp: **2026-10-08 15:03:55 UTC**.

A failed full API refresh stops the downstream full publication path. The last successful deployment remains live.

### Accreditation Publication Control

Workflow: `.github/workflows/watch-accreditation.yml`  
Generator: `scripts/process_accreditation_batch.py`  
Nominal schedule: **every 15 minutes**.

APC processes only explicit accreditation-letter requests entered in Project 75. The listener first peeks for a pending request; the heavier R/APC steps run only when a request exists.

The substantive accreditation event is the SCEPD `accreditation_date`. Once recorded, the verified refresh may establish the first accreditation date, generate the immutable course code, update accreditation/lifecycle status and determine catalogue eligibility. `approval_date` and `approval_reference` belong to the later APC letter/publication-control transaction and do not gate course-code generation. Historical valid references are preserved; gaps are not compacted merely to make numbering continuous.

### Project 79 certificate listener

Workflow: `.github/workflows/watch-certificates.yml`  
Generator: `scripts/process_certificate_requests.py`  
Nominal schedule: **every 15 minutes**.

The listener requires an explicit generation request plus approved participant/attendance/certificate fields. Its permitted Project 79 write-back is narrowly limited to uploading `certificate_file`, setting generated/date fields and clearing the generation request after success.

**Current scope remains controlled, not a general all-course certificate engine.** The script presently supports template `MUHAS_STD_01` and the configured run `DCEPD-SOP-173-2026_ARUSHA_20260928`. Requests from unsupported batches are skipped. The workflow limits one processing cycle to at most 10 eligible records.

Generated does not mean issued. Certificate issue remains a staff action. The current renderer also depends on approved logo assets fetched at runtime; this dependency should be considered when productionising additional runs.

### Course Director Applicant Packs

Workflow: `.github/workflows/watch-project79-applicant-packs.yml`  
Generator: `scripts/process_project79_applicant_packs.py`  
Nominal schedule: **05:15 EAT daily**, after the daily refresh.

The workflow is read-only against REDCap. It creates `All Applicants`, `Selection Return` and `Cert-Graduands Return` workbooks by course and uses the verified Project 75 Course Director/contact details for recipient QC.

Delivery rules are now:

- preserve the completed historical bootstrap state;
- from the Design Lock cutover, exclude partial/generic/invalid run attempts from operational packs;
- during current operation, send at most one updated pack per daily workflow run whenever at least one new valid current-fiscal-year application exists;
- include `applied_run_id` in the workbook and prefill the Selection Return batch ID from that run where no staff batch override already exists;
- keep delivery state in `automation/applicant-pack-state.json`.

The workflow checks SMTP/email secrets first. If email configuration is incomplete it falls back to **safe dry-run mode**, builds QC/output where possible and does not advance delivery state.

The first live bootstrap completed on **6 October 2026**, with **73 Applicant Packs** sent and delivery state persisted. During the subsequent health review, a mapping defect was identified: Project 79 choice IDs had been treated as if they were Project 75 record IDs. That assumption is now prohibited.

The current mapping contract is:

- `automation/project79-course-crosswalk.csv` is the repository copy of the verified Project 79 → Project 75 course crosswalk;
- Applicant Packs resolve every `applied_course_id` through that crosswalk before choosing the Project 75 Course Director;
- the public dashboard uses the same verified crosswalk;
- the full scheduled/manual API refresh promotes the latest verified crosswalk from the Project 75 runtime archive back into the repository;
- a Project 79 choice missing from the verified crosswalk fails closed/QC rather than being guessed from a numeric ID.

Delivery state in `automation/applicant-pack-state.json` remains keyed by the **Project 79 choice ID**, so prior send history is preserved even when the corresponding Project 75 record ID is different.

Returned workbooks are not auto-imported. A Coordinator/Admin saves the intended return sheet as **CSV UTF-8 (Comma delimited)** and imports it deliberately into Project 79.

A Project 79 record is an application attempt. For records dated **8 October 2026 onward**, dashboard and Applicant Pack processing treat it as an operational application only when the survey is complete and `applied_run_id` resolves to a real Course Run Log instance of the mapped Project 75 course. Earlier application history is preserved under the legacy course-level rule.

Project 79 course-choice metadata is also reviewed by `scripts/build_project79_course_choice_qc.py`. Its artifact reports `ADD_CHOICE`, `UPDATE_LABEL`, unmapped choices and crosswalk exceptions; it never writes REDCap metadata.

Payment fields remain distinct:

- `payment_reference`: applicant-provided payment/reference information;
- `gepg_control_no`: official staff-recorded GePG control number, when available;
- `fee_verified`: staff verification/check of fee/payment status.

A GePG control number alone does not confirm payment.

### Management reporting

`scripts/build_dcepd_management_packet.py` runs after successful scheduled/manual full API refreshes and creates:

- `management_summary.json`
- `management_summary.md`
- `action_list.csv`
- `overdue_reaccreditation.csv`

These are uploaded as `dcepd-management-<github_run_id>` with 90-day retention.

There is **no separate weekly management-email workflow in the current repository**. Any earlier Friday-email distribution plan should be treated as a proposed/historical arrangement unless a dedicated workflow is added and verified.

## Closed one-time maintenance

The approved Project 75 suspect-fee cleanup was completed on 6 October 2026. The live audit verified **142 manifest records, 142 eligible, 0 skipped, and 142 blank after write**. The one-time cleanup workflow is retained only as an auditable record of that intervention; it is not part of routine operation and should not be rerun without a new explicit approval and a fresh preflight.

## Safety rules

- Never write REDCap metadata/data dictionaries through the API.
- Do not expose the Project 79 staff-only instrument as a survey.
- Do not invent approval references, course codes, attendance, payments or certificate decisions.
- Do not turn missing/failed source data into false zero.
- Preserve historical course codes, accreditation references, Application IDs and certificate serials.
- Public catalogue/dashboard code remains read-only toward Project 79.
- Applicant-level packs are private and must only go to the verified Course Director and authorized DCEPD recipients.
- Never assume a Project 79 dropdown choice ID equals a Project 75 record ID; all downstream joins must use the verified Project 79 → Project 75 crosswalk.

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

For step-by-step technical procedures, use `automation/project75/TECHNICAL_USER_MANUAL.md`.

## Development

Python 3.12 is used for the public refresh, APC support, certificate listener and Applicant Pack components. The Project 75 verified refresh runtime uses R.

Run public-site tests with:

```bash
python -m unittest discover -s tests -p 'test_dcepd*.py'
```

The public deployment stages an explicit allowlist only. No OpenAlex dependency exists in this repository.
