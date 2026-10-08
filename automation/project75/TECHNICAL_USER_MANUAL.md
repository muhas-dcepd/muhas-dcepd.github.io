# DCEPD Technical User Manual

**System:** MUHAS DCEPD Short-Course Registry, Applications, Catalogue and Automation  
**Repository:** `muhas-dcepd/muhas-dcepd.github.io`  
**Operational baseline:** 8 October 2026  
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

As of 8 October 2026, the approved operational structure is the live Project 75/79 structure used by the green run-aware catalogue/dashboard build. Historical static field counts in earlier notes must not be used as the change-control authority because both projects evolved during Design Lock closure.

Project 75 retains:
- `course_registry`;
- repeating `course_run_log`;
- repeating `accreditation_publication_control`;
- `public_catalogue_details`.

Project 79 retains:
- `short_course_application`;
- staff-only `participant_selection_certification`;
- run-aware application context including `applied_run_id` and the course-level document requirement flags;
- the generic-entry catalogue notice and required `catalogue_entry_guard` Stop Action.

Verified operational snapshot:
- Project 75 master courses: **195**;
- public catalogue: **86 courses**;
- Course Run Log instances read: **320**;
- Project 79: **993 valid operational applications from 1,012 attempt records**;
- public catalogue source timestamp: **2026-10-08 15:03:55 UTC**.

The generic Project 79 survey route must remain fail-closed. Without run context, it must direct the user back to the catalogue and must not present a generic entry as a successfully received course application. The survey completion message is deliberately neutral; the application-received email remains the transactional confirmation for a valid submission.

During legacy run cleanup, `run_participants` may be temporarily editable so known historical participant counts can be entered. Unknown values remain blank, never forced to zero. When the legacy cleanup is closed, restore the approved read-only/derived control so future participant totals come from verified attendance.

A structural-guard failure means the live REDCap configuration no longer matches the approved automation contract. **Do not work around the guard.** Review the REDCap structure and the documented contract first.

## 5. Important accreditation rules

The SCEPD `accreditation_date` is the substantive accreditation event.

When appropriate, the verified refresh may use it to:

- establish the first-ever accreditation date;
- generate the immutable course code;
- update lifecycle/accreditation status; and
- determine catalogue eligibility.

`approval_date` and `approval_reference` belong to the later APC letter/publication-control process. They **do not gate course-code generation**.

Course codes are historical identifiers. Reaccreditation does not change the first accreditation date or an existing valid course code.


## 5A. Core data model the technical user must recognize

The earlier 2 October handoff remains useful because it documented the field-level operating model. The current system preserves that model, with later automation changes layered on top.

### Project 75 master-course inputs

Important source/identity fields include:

- `record_id`
- `course_name`
- `course_code`
- `date_submitted`
- `review_sent_date`
- `curricular_attached`
- `reviewer_1`, `reviewer_2`
- `accreditation_date`
- `accreditation_date_first`
- `approval_date`
- `approval_reference`
- `cpd_points`
- `course_director_id`
- `contact_phone`
- `contact_email`
- `course_department_code`
- `course_school_code`
- `fee_per_person_tsh`
- reviewer-payment fields where used.

### Project 75 derived fields

The verified refresh maintains, where applicable:

- `dormant_flag`
- `curriculum_type`
- `course_status`
- `accreditation_status`
- `public_catalogue`
- accreditation calendar/fiscal fields
- `interested_applicants`
- `interested_applicants_updated_at`
- `times_conducted`
- `first_date_conducted`
- `last_date_conducted`
- `total_participants`
- `total_income_tsh`.

### Repeating Course Run Log

The repeating `course_run_log` contains delivery-level facts such as:

- run start/end date;
- participants;
- run days;
- run director/unit fields;
- run income where known;
- derived calendar year, month, fiscal quarter and fiscal year.

A repeat delivery is **not** a new course master record.

### Project 79 participant/certification fields

The staff-only `participant_selection_certification` instrument contains the controlled participant workflow, including:

- selection and batch fields;
- attendance verification;
- certificate approval;
- certificate running sequence and visible certificate number;
- template readiness;
- explicit certificate-generation request;
- generated certificate status/date/file;
- certificate-issued status/date;
- manual-certificate flag and notes.

The REDCap Project 79 `record_id` remains the operational Application ID. Do not create a parallel numbering system.


## 6. Routine GitHub workflows

The current repository has five GitHub Actions workflows. The technical user should distinguish the **full verified REDCap refresh** from the lighter **push/publication path**.

### 6.1 Full REDCap refresh and website deployment

Workflow: `.github/workflows/update-dcepd.yml`

Triggers:

- daily schedule: **04:37 EAT** (`37 1 * * *` UTC);
- manual dispatch with `refresh_api=true`;
- pushes to `main`.

Only the daily schedule and manual dispatch with `refresh_api=true` run the R Project 75/79 verified sync. That full path:

1. reconstructs the checksum-verified V2.2.12 Project 75 runtime;
2. applies the maintained V2.2.13 compatibility patch;
3. runs the live Project 75/79 refresh with structural guards;
4. blocks live Project 75 writes on QC errors;
5. writes only approved Project 75 derived record values in verified batches;
6. uploads the `project75-sync-<run_id>` audit artifact;
7. rebuilds the public catalogue and aggregate dashboard directly from the APIs;
8. builds and uploads the management packet;
9. runs the public-site test suite and SEO/sitemap generation;
10. commits generated public outputs if changed; and
11. deploys GitHub Pages.

A push to `main` follows a different path: it **does not run the R sync** and does not build the Project 75 technical/management artifacts. It does, however, fetch the Project 75/79 APIs for the public catalogue/dashboard, run tests/SEO and deploy Pages. Documentation commits can therefore trigger a public refresh commit if generated files change.

Manual dispatch with `refresh_api=false` skips both the R sync and the API catalogue/dashboard refresh; it uses the current generated files for the test/stage/deploy path.

If the full verified API refresh fails, downstream full publication stops. Do not bypass the failed stage.

### 6.2 Accreditation Publication Control listener

Workflow: `.github/workflows/watch-accreditation.yml`  
Primary scripts: `process_accreditation_batch.py`, `repair_accreditation_references.py`, `mark_accreditation_failure.py`  
Schedule: **every 15 minutes**.

The listener first performs a lightweight peek. Heavy R/APC processing runs only when a pending request exists.

For a valid request the workflow:

1. runs a normal verified Project 75 refresh;
2. checks/repairs genuine duplicate approval references;
3. claims the requested APC instance;
4. writes the controlled approval reference/date transaction;
5. runs verified Project 75 refresh again;
6. finalizes accreditation DOCX letters and the register/ZIP package;
7. uploads APC and technical audit artifacts;
8. refreshes public outputs and management packet; and
9. deploys the refreshed public site.

The manual `resume_instance` input is for a deliberate retry of one known failed APC repeat instance, not for bypassing APC state.

### 6.3 Project 79 certificate listener

Workflow: `.github/workflows/watch-certificates.yml`  
Generator: `scripts/process_certificate_requests.py`  
Schedule: **every 15 minutes**.

Eligibility currently requires:

- explicit `certificate_generation_requested=1`;
- not already generated;
- selected for batch;
- participant role;
- attendance verified;
- certificate approved;
- running certificate sequence present;
- full visible certificate number present;
- template ready;
- template code `MUHAS_STD_01`.

The current backend is still **run-configured and limited**, not a general all-course certificate engine. At this checkout it supports the configured batch:

`DCEPD-SOP-173-2026_ARUSHA_20260928`

The workflow processes at most **10** eligible records per cycle. Unsupported batches are skipped.

The renderer obtains course title and Course Director from Project 75 and writes back only the approved certificate-generation fields/file to Project 79. It fetches the Government and MUHAS logo assets at render time, so external logo availability is a current technical dependency.

After a successful PDF upload the backend:

- sets `certificate_generated=1`;
- writes `certificate_generated_date`; and
- resets `certificate_generation_requested=0`.

It does **not** mark the certificate issued. Reissue/cancellation remains manual until a formal controlled pathway is implemented.

### 6.4 Course Director Applicant Packs

Workflow: `.github/workflows/watch-project79-applicant-packs.yml`  
Generator: `scripts/process_project79_applicant_packs.py`  
Schedule: **05:15 EAT daily** (`15 2 * * *` UTC).

This workflow is read-only against REDCap. It produces three sheets per course:

- `All Applicants`
- `Selection Return`
- `Cert-Graduands Return`

Returned sheets are deliberately imported by an authorized Coordinator/Admin after saving the intended sheet as **CSV UTF-8 (Comma delimited)**.

Current send logic:

1. bootstrap the historic applications for each course once;
2. after bootstrap, send when 5 or more new current-FY applications exist;
3. on Friday, catch up when 1–4 new current-FY applications exist.

Recipient/contact QC uses Project 75 Course Director/contact metadata. Delivery state is stored in `automation/applicant-pack-state.json`.

The workflow now validates mail configuration before any live send. If SMTP/email secrets are incomplete, it forces safe dry-run mode and does not advance state.

**Current checkout status:** the first live bootstrap completed on 6 October 2026 with **73 Applicant Packs** sent and delivery state persisted. A subsequent mapping defect showed why Project 79 choice IDs must never be treated as Project 75 record IDs. The verified crosswalk is now mandatory for recipient/course resolution, and unresolved mappings fail closed/QC.

### 6.5 One-time Project 75 suspect-fee cleanup

Workflow: `.github/workflows/one-time-project75-fee-cleanup.yml`

The workflow remains in the repository only as an auditable maintenance mechanism. Manual dispatch defaults to `execute=false`; execution requires explicit `execute=true`.

The approved October intervention is complete: **142/142** targeted suspect fee values were verified blank. Do not reuse the retained workflow for a new cleanup without a new manifest, new preflight and explicit approval.

### 6.6 Management reporting

The full scheduled/manual API refresh runs `scripts/build_dcepd_management_packet.py` and uploads:

`dcepd-management-<github_run_id>`

for 90 days.

The packet contains:

- `management_summary.json`
- `management_summary.md`
- `action_list.csv`
- `overdue_reaccreditation.csv`

The current repository does **not** contain a separate weekly email/distribution workflow for this management packet. If management email distribution is required, implement and verify it as a distinct controlled workflow rather than assuming the historical Friday plan is active.

## 6.5 Human decisions versus automated transactions

The system deliberately separates institutional judgement from transaction execution.

The following remain human decisions:

- course approval and accreditation;
- reviewer assignment and review conclusions;
- participant selection;
- attendance verification;
- certificate approval;
- certificate serial allocation policy;
- signatory approval;
- partner/sponsor branding approval;
- certificate issue;
- reissue/cancellation decisions;
- correction of historical exceptions.

Automation may execute an already-approved action. It must not infer or manufacture the underlying decision.

### Certificate identity rules

- `certificate_seq` is the central running integer and is never reused.
- The visible `certificate_serial_no` is the full certificate identifier.
- Application ID remains separate from the certificate number.
- A generated PDF is not equivalent to an issued certificate.
- Reissue/cancellation must be explicit; never silently regenerate over an issued certificate.


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


## 10A. APC technical rules

APC is a controlled transaction, not a side effect of the daily refresh.

Important principles retained from the earlier technical handoff:

- scheduled refreshes alone must not allocate accreditation references or generate letters;
- historical valid references are preserved;
- gaps are not compacted merely to make numbering look continuous;
- duplicate-reference repair must preserve the canonical valid occurrence and act only on genuine duplicates;
- a failed APC transaction must remain reviewable rather than being hidden by a second competing reference.

The authoritative accreditation-letter template remains under the repository accreditation assets. When template layout or signatory practice changes, treat that as a controlled document/automation change, not an ad-hoc edit during a live batch.


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


## 15A. Recovery lessons from the September 2026 incident

The prohibition on metadata API writes is not theoretical. The September 2026 recovery demonstrated that metadata/data-dictionary writes on this REDCap installation can cause destructive structural loss.

Therefore:

1. structural restoration comes before record restoration;
2. do not import record backups into a damaged dictionary;
3. after restoring structure, verify whether stored record values reappear;
4. confirm structural guards pass before returning automation to live operation;
5. preserve emergency recovery packages outside the public repository.


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

## 18. Relationship to the 2 October 2026 documents

The 2 October 2026 user manual and technical handoff are the historical design/operational baseline for this documentation set. Their durable rules on REDCap ownership, human decision-making, certificate identity, APC controls, recovery and public/private separation remain incorporated here. Where they differ from the live repository, the **6 October 2026 repository state governs** — notably current workflow names, 15-minute listeners, expanded structural baselines, Applicant Packs, the current single-run certificate listener and the completed fee cleanup.

The older end-user manual remains valuable for Directors, Coordinators and Administrators because it explains the day-to-day REDCap workflow without requiring GitHub knowledge. It is conceptually distinct from this technical administrator manual.

## 19. Closeout status

The core system is now in **routine operations / handover phase** under the 8 October 2026 Design Lock V1 closeout.

The run-aware catalogue/dashboard pipeline has passed a successful push-based build and deployment. Courses remain visible when closed; application buttons are run-specific and appear only for eligible open runs. Project 79 generic entry fails closed through the catalogue notice plus required Stop Action guard.

Remaining work is operational rather than architectural:
- review Project 79 course-choice QC items and make approved manual metadata changes where required;
- continue ordinary course/run administration;
- finish legacy run participant backfill, then restore the approved read-only/derived participant control;
- maintain certificate expansion as a separately approved enhancement rather than assuming the current controlled listener is universal;
- preserve recovery material and structural-change discipline.

Future work should be classified as routine data administration, operational incident/fix, approved structural change, approved feature enhancement, or recovery exercise. Do not reopen the core Project 75/79 architecture for ordinary maintenance.
