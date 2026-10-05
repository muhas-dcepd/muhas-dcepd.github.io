# DCEPD Technical User Manual

**System:** MUHAS DCEPD Short-Course Registry, Applications, Catalogue and Automation  
**Repository:** `muhas-dcepd/muhas-dcepd.github.io`  
**Operational baseline:** 6 October 2026  
**Audience:** DCEPD technical administrator / system custodian

## 1. Purpose

This manual is for the technical user responsible for keeping the DCEPD digital short-course system operational. It complements:

- the repository-level `README.md`, which explains the overall system and its public/automation boundaries; and
- `automation/project75/HANDOFF.md`, which records institutional continuity, locked rules, recovery information and historical baselines.

This manual focuses on **what the technical user should actually do** during routine operation, manual refreshes, workflow failures, controlled changes and recovery.

## 2. System at a glance

The system has four operational layers:

1. **REDCap Project 75 — authoritative short-course registry**
   - one master record per course;
   - repeating `course_run_log` for deliveries;
   - repeating `accreditation_publication_control` (APC) for accreditation-letter/publication control;
   - `public_catalogue_details` for approved public-facing course information.

2. **REDCap Project 79 — applications and participant workflow**
   - `short_course_application` for applicants;
   - staff-only `participant_selection_certification` for selection, batching, attendance/payment verification and certification.

3. **GitHub automation**
   - maintains approved derived Project 75 record values;
   - processes explicit accreditation and certificate requests;
   - prepares Course Director Applicant Packs;
   - builds management outputs;
   - never uses the API to modify REDCap metadata/data dictionaries.

4. **Public GitHub Pages site**
   - `/dcepd-courses/` — public catalogue;
   - `/dcepd-dashboard/` — aggregate activity/application dashboard;
   - read-only public output only.

## 3. Locked safety boundaries

The technical user must preserve the following rules.

- **Never write REDCap metadata/data dictionaries through the API.**
- **Project 79 is read-only to the main Project 75 sync.**
- Never enable `participant_selection_certification` as a public survey.
- Do not renumber or silently rewrite historical course codes, accreditation references, Application IDs or certificate serials.
- Do not invent missing attendance, payments, dates, accreditation references or participant counts.
- Do not convert failed/missing source data into zero.
- Do not bypass batch verification for Project 75 writes.
- Do not publish raw REDCap exports or applicant-level information.
- `public_catalogue` remains the sole public-visibility flag.
- A GePG control number does not, by itself, prove payment.
- Generated certificates are not automatically considered issued.

## 4. Current verified structural baseline

As of 6 October 2026:

- Project 75: **80 fields**;
- Project 75 instruments:
  - `course_registry`
  - repeating `course_run_log`
  - repeating `accreditation_publication_control`
  - `public_catalogue_details`
- Project 79: **73 fields**;
- Project 79 instruments:
  - `short_course_application`
  - staff-only `participant_selection_certification`
- Project 75 master courses: **195**;
- public catalogue: **86 courses**.

A structural-guard failure means the live REDCap configuration no longer matches the approved automation baseline. **Do not work around the guard.** Review the REDCap structure first.

## 5. Important accreditation rules

The SCEPD `accreditation_date` is the substantive accreditation event.

When appropriate, the verified refresh may use it to:

- establish the first-ever accreditation date;
- generate the immutable course code;
- update lifecycle/accreditation status; and
- determine catalogue eligibility.

`approval_date` and `approval_reference` belong to the later APC letter/publication-control process. They **do not gate course-code generation**.

Course codes are historical identifiers. Reaccreditation does not change the first accreditation date or an existing valid course code.

## 6. Routine GitHub workflows

### 6.1 Full REDCap refresh and website deployment

Workflow: `.github/workflows/update-dcepd.yml`

Schedule: **04:37 EAT daily** (`37 1 * * *` UTC).

The scheduled full refresh:

1. validates/reconstructs the verified Project 75 runtime;
2. applies the maintained V2.2.13 compatibility patch;
3. exports and validates Projects 75 and 79;
4. calculates proposed derived Project 75 state;
5. blocks live writes when QC errors are present;
6. imports approved Project 75 record changes in verified batches;
7. verifies final Project 75 state;
8. builds the public catalogue and dashboard;
9. builds the management reporting packet;
10. runs public-site tests and SEO generation;
11. commits generated public outputs when changed; and
12. deploys GitHub Pages.

If the full refresh fails, downstream publication stops. The last successful deployment remains live.

### 6.2 Accreditation Publication Control listener

Workflow: `.github/workflows/watch-accreditation.yml`

Schedule: **every 15 minutes**.

The listener processes only explicit pending APC requests in Project 75. It runs the normal verified Project 75 refresh before claiming a request, prepares the accreditation package, refreshes the catalogue/dashboard after successful processing and records workflow artifacts.

A failed APC request should be corrected before retrying. The manual workflow input `resume_instance` exists for an explicit controlled retry of one failed APC repeat instance.

### 6.3 Project 79 certificate listener

Workflow: `.github/workflows/watch-certificates.yml`

Schedule: **every 15 minutes**.

It checks explicit certificate-generation requests, applies eligibility rules and processes a limited number per run. The permitted write-back is restricted to certificate generation fields/file handling.

**Generated does not mean issued.** Issuance remains a staff decision/action.

### 6.4 Course Director Applicant Packs

Workflow: `.github/workflows/watch-project79-applicant-packs.yml`

Schedule: **05:15 EAT daily** (`15 2 * * *` UTC).

The workflow is read-only against REDCap. It builds/sends Course Director packs and maintains delivery state in:

`automation/applicant-pack-state.json`

Manual workflow dispatch defaults to **dry run = true**. Keep dry run enabled when testing configuration or QC. A live manual send should only be done deliberately after confirming recipients, SMTP configuration and expected pack content.

Returned Excel workbooks are **not auto-imported**. An authorized Coordinator/Admin must save the intended return sheet as **CSV UTF-8 (Comma delimited)** and deliberately import it into Project 79.

## 7. How to run a manual full refresh

Use this when the scheduled refresh needs to be rerun after a corrected source-data or technical problem.

1. Open the repository on GitHub.
2. Go to **Actions**.
3. Select **Refresh and deploy MUHAS DCEPD**.
4. Choose **Run workflow**.
5. Keep **Refresh both REDCap feeds before publishing = true** for a true full refresh.
6. Start the workflow.
7. Follow the build steps until completion.
8. Confirm the deploy job also succeeds.
9. Check the public catalogue and dashboard only after the workflow is green.

Do not repeatedly rerun a failed workflow without understanding the cause.

## 8. What to inspect after a full refresh

### Technical audit artifact

Artifact:

`project75-sync-<github_run_id>`

Important files include:

- `output/run_*/project75_qc_summary.csv`
- `output/run_*/project75_qc_issues.csv`
- `output/run_*/verification_master_differences.csv`
- `output/run_*/verification_run_differences.csv`
- `logs/project75_v2_2_*.log`
- `archive/verified/*`

A healthy completed live refresh should end with no unresolved verification differences.

### Management artifact

Artifact:

`dcepd-management-<github_run_id>`

Contains:

- `management_summary.json`
- `management_summary.md`
- `action_list.csv`
- `overdue_reaccreditation.csv`

These are management outputs. They should not be confused with the technical audit.

## 9. Failure triage

When a workflow fails, first identify **which workflow and which step** failed.

### A. Structural validation failure

Likely meaning: Project 75 or Project 79 metadata/forms no longer match the approved baseline.

Action:

1. stop;
2. inspect the actual REDCap structure;
3. determine whether a deliberate manual metadata change was made;
4. correct/restore the REDCap dictionary as appropriate;
5. update automation only after the new structure is deliberately approved.

Do **not** weaken the structural guard simply to make the workflow green.

### B. QC error before Project 75 write

Likely meaning: the exported source data violate a protected business/data rule.

Action:

1. inspect `project75_qc_issues.csv`;
2. correct the underlying REDCap record(s) where justified;
3. rerun from a fresh export.

Do not manually force later pipeline stages.

### C. Project 75 import or verification failure

Action:

1. inspect the R log and verification difference files;
2. determine whether the failure is API/network-related or a record-state mismatch;
3. do not edit generated output files to hide the mismatch;
4. rerun only after the cause is understood.

The next run begins from a fresh export and proposes only what remains incorrect.

### D. Public catalogue/dashboard build failure

Action:

1. confirm whether the REDCap sync itself succeeded;
2. review Python/test output;
3. correct code/taxonomy/template issues;
4. rerun the full workflow.

Do not publish partial generated files manually unless performing a deliberate controlled recovery.

### E. Applicant Pack email failure

Action:

1. check whether the run was dry-run or live;
2. verify SMTP secrets/configuration;
3. inspect the Applicant Pack artifact/QC;
4. confirm whether `automation/applicant-pack-state.json` advanced.

If email was sent but state persistence failed, review carefully before rerunning to avoid unintended duplicate delivery.

### F. Accreditation listener failure

Action:

1. inspect the failed run and APC record;
2. correct the reported problem;
3. use the explicit `resume_instance` manual input only when resuming the known failed instance is appropriate.

Do not create replacement approval references simply to get around an error.

### G. Certificate listener failure

Action:

1. inspect the Project 79 request and workflow log;
2. verify eligibility/source fields;
3. correct the source problem;
4. rerun the listener.

Do not mark a certificate issued merely because a PDF was generated.

## 10. REDCap metadata changes

Choice lists, year lists, organisational lists, new fields, form configuration and survey configuration are **manual REDCap administration**.

Before making a structural change:

1. document the reason;
2. identify affected workflows/scripts;
3. export/record the current dictionary;
4. make the change manually in REDCap;
5. update structural guards and code deliberately;
6. test safely;
7. update this manual, the main README and/or HANDOFF when the operational contract changes.

Never use the API to write the REDCap data dictionary.

## 11. Secrets and credentials

Required REDCap secrets:

- `REDCAP_PROJECT75_TOKEN`
- `REDCAP_PROJECT79_TOKEN`

Email-enabled workflows additionally use:

- `DCEPD_EMAIL_1` to `DCEPD_EMAIL_4`
- `DCEPD_SMTP_HOST`
- `DCEPD_SMTP_PORT` when needed
- `DCEPD_SMTP_USERNAME`
- `DCEPD_SMTP_PASSWORD`

Never place token or password values in source files, documentation, committed logs or public artifacts.

If a credential is believed to be exposed, rotate it rather than merely deleting the visible copy.

## 12. Local Project 75 runtime

The maintained GitHub runtime is:

**V2.2.12 checksum-verified base + V2.2.13 compatibility patch**

The workflow reconstructs the base package from:

`automation/project75-v2.2.12-runtime.b64.part*`

and validates SHA256 before applying the compatibility patch.

For local use, dry run is the safe default. A live local run requires both REDCap token environment variables and an explicit live setting. Do not save tokens into R files or shell scripts.

## 13. Public catalogue rules

The catalogue is a downstream, read-only representation of Project 75.

Only records with `public_catalogue = Yes` are published.

The catalogue generator does not independently override accreditation/dormancy/publication eligibility. Search taxonomy and secondary-subject discovery help users find courses but do not change visibility.

Private contact details, applicant identities, payment information and management-only fields must never be added to the public schema.

## 14. One-time maintenance scripts

The Project 75 suspect-fee cleanup completed on 6 October 2026 with **142/142 targeted records verified blank**.

The retained workflow/script is an audit trail of that intervention. It is **not routine operation**.

Do not rerun a one-time maintenance workflow without:

1. a new explicit management/technical decision;
2. a fresh target manifest/preflight;
3. verification that the current live records meet the intended eligibility criteria; and
4. a documented rollback/recovery approach.

## 15. Recovery

Emergency recovery packages are institutional recovery material and should remain outside the public repository:

- `Project75_EMERGENCY_RECOVERY_2026-09-25.zip`
- `Project79_EMERGENCY_RECOVERY_FIXED_2026-09-25.zip`

Known verified reference points include:

- local verified baseline: `archive/verified/20260926_000640`
- first successful GitHub-hosted verified baseline: `archive/verified/20260926_064450`

If structural loss is suspected:

1. stop automation;
2. restore the correct REDCap dictionary first;
3. verify whether stored record data reappear;
4. only then consider record-level restoration;
5. run the system in a safe verification/dry-run mode before returning to live operation.

Metadata API import remains prohibited during recovery.

## 16. Routine technical-user checklist

### Daily / when alerts arrive

- Check failed GitHub Action notifications.
- Identify the exact failed workflow and step.
- Distinguish technical failure from management/QC exception.
- Avoid unnecessary manual edits when the last successful public deployment is still live.

### Weekly

- Review the management summary/action list.
- Review overdue reaccreditation items.
- Check repeated workflow failures or warnings for a pattern.
- Confirm Applicant Pack delivery state is advancing normally.

### After deliberate REDCap structural changes

- Confirm Project 75/79 field counts and instrument names.
- Update guards/code where approved.
- Run a controlled test/full refresh.
- Confirm verification files are clean.
- Update technical documentation.

### After code/workflow changes

- Run the public-site test suite:
  ```bash
  python -m unittest discover -s tests -p 'test_dcepd*.py'
  ```
- Prefer dry-run/testing paths for write-capable components.
- Review generated public data for accidental disclosure before deployment.

## 17. Documentation hierarchy

Use the three documents together:

- **Root `README.md`** — system overview, boundaries, workflows and closeout baseline.
- **`automation/project75/TECHNICAL_USER_MANUAL.md`** — routine operating instructions for the technical user.
- **`automation/project75/HANDOFF.md`** — institutional continuity, locked rules, historical/recovery context and transfer of custodianship.

When the system changes, update the document(s) whose operational contract actually changed rather than adding ad-hoc notes elsewhere.

## 18. Closeout status

The core system is now in **routine operations / handover phase**.

Future work should be classified as one of:

- routine data administration;
- operational incident/fix;
- approved structural change;
- approved feature enhancement; or
- recovery exercise.

Do not treat ordinary maintenance as a reason to redesign the core Project 75/79 architecture.
