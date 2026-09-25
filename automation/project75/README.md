# DCEPD Project 75 / Project 79 REDCap Sync

**Release:** V2.2.12 — GitHub cron release  
**Timezone:** Africa/Dar_es_Salaam  
**Primary registry:** REDCap Project 75  
**Applications:** REDCap Project 79

## Purpose

This workflow maintains derived **record values** in Project 75 from the authoritative course registry, repeating Course Run Log, and Project 79 applications. It is the same record-only workflow that passed supervised LIVE verification on 26 September 2026.

## Permanent safety boundary

**The automation never writes REDCap metadata/data dictionaries.** Metadata is exported and checked only. Required dictionary changes are reported as manual actions. Project 79 is read-only.

Project 75 record imports are sent in small verified batches to stay below the MUHAS Apache POST-size limit. Each batch is re-exported and verified before the workflow continues. A verified archive is promoted only after final verification passes.

## Derived Project 75 values

The workflow maintains, where applicable:

- first-ever accreditation date establishment for future formally approved courses;
- immutable course-code generation when approval/accreditation gates are satisfied;
- lifecycle `course_status`;
- rolling two-year dormancy;
- three-year accreditation validity and `curriculum_type`;
- `public_catalogue`;
- accreditation calendar/fiscal derived values;
- run-log calendar/fiscal derived values;
- delivery summaries (`times_conducted`, first/last run dates, participants, income where known);
- `interested_applicants` from Project 79.

`interested_applicants_updated_at` changes only when that course's applicant count changes.

## Local use

Dry run is the default:

```r
source("project75_refresh_v2_2.R")
```

To run LIVE locally, set the two token environment variables and either set `DCEPD_DRY_RUN=false` or change the local config temporarily. Do not store tokens in source files.

Required environment variables:

- `REDCAP_PROJECT75_TOKEN`
- `REDCAP_PROJECT79_TOKEN`

## GitHub Actions

The repository workflow runs this sync before the public DCEPD catalogue/dashboard refresh on scheduled/manual API refreshes. GitHub secrets use the same two names above. Runtime outputs are retained as workflow artifacts instead of being committed to the public repository.

## Recovery baseline

Keep the 25–26 September 2026 emergency recovery packages and the verified local baseline `archive/verified/20260926_000640` outside the public repository as institutional recovery material.
