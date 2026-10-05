# Project 75 verified REDCap sync

Current runtime: **V2.2.12 base + V2.2.13 compatibility patch**.

This folder carries the versioned runtime package used by the DCEPD GitHub Actions refresh.

## Safety

- REDCap metadata/data-dictionary writes are disabled.
- Project 79 is read-only.
- Project 75 record imports are batched and verified after each batch.
- Structural guards require the current approved baseline: Project 75 **80 fields** across `course_registry`, `course_run_log`, `accreditation_publication_control`, and `public_catalogue_details`; Project 79 **73 fields** across `short_course_application` and staff-only `participant_selection_certification`.
- Tanzania time (`Africa/Dar_es_Salaam`) is enforced.
- `interested_applicants_updated_at` changes only when the applicant count changes.
- Failure of the R sync stops the downstream catalogue/dashboard refresh.

## Runtime integrity

The Base64 chunks reconstruct `project75-v2.2.12-runtime.zip`. The workflow then applies the maintained V2.2.13 patch before execution.

SHA256:

`3074e99682a3a1d338053e24f7c409ebaa6d47f5ea0acd4085d5286ee0c82a49`

The workflow checks this SHA before executing the package.

The full technical README and institutional HANDOFF are inside the runtime package. Keep the 25 September 2026 emergency recovery snapshots outside this public repository.


## October 2026 closeout

The 6 October verified full refresh produced a public catalogue of **86 courses**. SCEPD `accreditation_date` now drives first accreditation, immutable code generation and accreditation status; APC approval date/reference remain downstream letter-control fields. The approved one-time suspect-fee cleanup completed with **142/142** targeted records verified blank.
