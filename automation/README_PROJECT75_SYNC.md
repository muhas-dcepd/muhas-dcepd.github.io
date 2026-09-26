# Project 75 verified REDCap sync

Current release: **V2.2.12**.

This folder carries the versioned runtime package used by the DCEPD GitHub Actions refresh.

## Safety

- REDCap metadata/data-dictionary writes are disabled.
- Project 79 is read-only.
- Project 75 record imports are batched and verified after each batch.
- Structural guards require Project 75 to have 48 fields across `course_registry` and `course_run_log`, and Project 79 to have 53 fields in `short_course_application`.
- Tanzania time (`Africa/Dar_es_Salaam`) is enforced.
- `interested_applicants_updated_at` changes only when the applicant count changes.
- Failure of the R sync stops the downstream catalogue/dashboard refresh.

## Runtime integrity

The Base64 chunks reconstruct `project75-v2.2.12-runtime.zip`.

SHA256:

`3074e99682a3a1d338053e24f7c409ebaa6d47f5ea0acd4085d5286ee0c82a49`

The workflow checks this SHA before executing the package.

The full technical README and institutional HANDOFF are inside the runtime package. Keep the 25 September 2026 emergency recovery snapshots outside this public repository.
