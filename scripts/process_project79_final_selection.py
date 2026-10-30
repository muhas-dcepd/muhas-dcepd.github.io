#!/usr/bin/env python3
"""Scheduled, private, once-per-run final applicant selection delivery."""
import json
import os
from datetime import date, datetime
from pathlib import Path

import process_project79_applicant_packs as p

STATE = Path("automation/final-selection-delivery-state.json")
ACTIVATION = date(2026, 10, 30)

def main():
    today = datetime.now(p.TZ).date()
    state = json.loads(STATE.read_text()) if STATE.exists() else {"sent": {}}
    sent = state.setdefault("sent", {})
    p75 = p.export_records(p.P75_TOKEN, p.P75_FIELDS)
    masters = {str(r["record_id"]): r for r in p.master_rows(p75)}
    runs = {}
    for row in p75:
        if str(row.get("redcap_repeat_instrument", "")).strip() != "course_run_log":
            continue
        rid = str(row.get("record_id", "")).strip()
        instance = str(row.get("redcap_repeat_instance", "")).strip()
        run_id = str(row.get("run_batch_id", "")).strip()
        if not rid or not instance or run_id != f"{rid}-{instance}" or run_id in runs:
            raise ValueError("Duplicate or inconsistent Project 75 run identifier")
        runs[run_id] = row
    crosswalk = p.load_course_crosswalk()
    p79 = p.master_rows(p.export_records(p.P79_TOKEN, p.P79_FIELDS))
    grouped = {}
    for row in p79:
        run_id = str(row.get("applied_run_id", "")).strip()
        if run_id in runs:
            mapped = crosswalk.get(str(row.get("applied_course_id", "")).strip())
            if mapped != run_id.split("-", 1)[0]:
                raise ValueError("Project 79 applicant course/run mismatch")
            grouped.setdefault(run_id, []).append(row)
    metadata = p.export_metadata(p.P79_TOKEN)
    labels = {field: p.choice_map(metadata, field) for field in p.DIRECTOR_FIELDS}
    director_labels = p.choice_map(p.export_metadata(p.P75_TOKEN), "course_director_id")
    eligible_runs = 0
    for run_id, run in sorted(runs.items()):
        close = p.parse_iso_date(run.get("run_application_close_date", ""))
        if close is None or close < ACTIVATION or close >= today or run_id in sent:
            continue
        course = masters.get(run_id.split("-", 1)[0])
        if not course or not grouped.get(run_id):
            print(f"SKIP run={run_id} reason=missing-course-or-applicants")
            continue
        email = str(course.get("contact_email", "")).strip()
        if not p.EMAIL_RE.match(email) or not course.get("course_director_id"):
            print(f"SKIP run={run_id} reason=unverified-director")
            continue
        course = dict(course)
        course["course_director_name"] = director_labels.get(str(course["course_director_id"]), "Course Director")
        eligible_runs += 1
        try:
            payload, exceptions = p.prepare_selection_package(
                course, run_id, grouped[run_id], {run_id}, labels=labels,
                mode="final", run_record=run, today=today, include_documents=True)
            if exceptions:
                print(f"SKIP run={run_id} reason=application-exceptions count={len(exceptions)}")
                continue
            if os.getenv("DCEPD_FINAL_SEND_ENABLED", "false").lower() != "true":
                print(f"DRY_RUN run={run_id} zip_bytes={len(payload)}")
                continue
            p.send_private_selection_zip(course, payload, run_id, "final", email)
            sent[run_id] = {"sent_at": datetime.now(p.TZ).isoformat(), "closing_date": close.isoformat()}
            STATE.parent.mkdir(parents=True, exist_ok=True)
            STATE.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
            print(f"SENT run={run_id} zip_bytes={len(payload)}")
        except Exception as exc:
            print(f"FAILED run={run_id} reason={type(exc).__name__}")
            raise
    print(f"Eligible closed runs examined: {eligible_runs}")

if __name__ == "__main__":
    main()
