#!/usr/bin/env python3
"""Build a management-facing DCEPD reporting packet from the latest verified Project 75 run.

This script is deliberately read-only. It does not call REDCap and does not modify the
public website. It converts the latest Project 75 QC/audit outputs into small JSON,
Markdown and CSV files suitable for management reporting.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Africa/Dar_es_Salaam")
KNOWN_NONACTIONABLE = {"KNOWN_PENDING_ACCREDITATION_1900"}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def data_row_count(path: Path) -> int:
    return len(read_csv(path))


def latest_run_dir(runtime: Path) -> Path:
    candidates = sorted((runtime / "output").glob("run_*"))
    if not candidates:
        raise SystemExit(f"No Project 75 output/run_* directory found under {runtime}")
    return candidates[-1]


def latest_verified_dir(runtime: Path) -> Path | None:
    candidates = sorted((runtime / "archive" / "verified").glob("*"))
    return candidates[-1] if candidates else None


def parse_catalogue_count(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        value = obj.get("count")
        return int(value) if value is not None else None
    except Exception:
        return None


def master_index(export_rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in export_rows:
        if not (row.get("redcap_repeat_instrument") or "").strip():
            rid = (row.get("record_id") or "").strip()
            if rid:
                out[rid] = row
    return out


def public_catalogue_label(row: dict[str, str]) -> str:
    value = (row.get("public_catalogue") or "").strip().lower()
    return "Yes" if value in {"1", "yes", "true"} else "No"


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runtime", default=".project75-runtime")
    ap.add_argument("--catalogue", default="dcepd-courses/catalogue.json")
    args = ap.parse_args()

    runtime = Path(args.runtime)
    run_dir = latest_run_dir(runtime)
    verified_dir = latest_verified_dir(runtime)
    out_dir = runtime / "management"
    out_dir.mkdir(parents=True, exist_ok=True)

    qc_summary = read_csv(run_dir / "project75_qc_summary.csv")
    qc_issues = read_csv(run_dir / "project75_qc_issues.csv")
    export_rows = read_csv(run_dir / "project75_export_verified_candidate.csv")
    if not export_rows:
        export_rows = read_csv(run_dir / "project75_export_raw.csv")
    master = master_index(export_rows)

    by_severity = Counter()
    by_issue = Counter()
    for row in qc_summary:
        n = int(row.get("issue_count") or 0)
        by_severity[(row.get("severity") or "").upper()] += n
        by_issue[(row.get("severity") or "").upper(), row.get("issue_code") or ""] += n

    enriched: list[dict[str, str]] = []
    for q in qc_issues:
        rid = (q.get("record_id") or "").strip()
        r = master.get(rid, {})
        enriched.append({
            "record_id": rid,
            "course_code": r.get("course_code", ""),
            "course_name": r.get("course_name", ""),
            "severity": q.get("severity", ""),
            "issue_code": q.get("issue_code", ""),
            "detail": q.get("detail", ""),
            "accreditation_date": r.get("accreditation_date", ""),
            "date_submitted": r.get("date_submitted", ""),
            "review_sent_date": r.get("review_sent_date", ""),
            "approval_date": r.get("approval_date", ""),
            "last_date_conducted": r.get("last_date_conducted", ""),
            "interested_applicants": r.get("interested_applicants", ""),
            "public_catalogue": public_catalogue_label(r),
        })

    overdue = [x for x in enriched if x["issue_code"] == "REACCREDITATION_OVERDUE"]

    def reaccreditation_in_progress(row: dict[str, str]) -> bool:
        """Use explicit newer resubmission evidence; never infer from a magic date."""
        try:
            acc = datetime.strptime((row.get("accreditation_date") or "").strip(), "%Y-%m-%d").date()
            submitted = datetime.strptime((row.get("date_submitted") or "").strip(), "%Y-%m-%d").date()
            return submitted > acc
        except (TypeError, ValueError):
            return False

    for x in overdue:
        x["reaccreditation_progress"] = (
            "Re-accreditation in progress" if reaccreditation_in_progress(x)
            else "No newer re-accreditation submission recorded"
        )

    overdue_in_progress = [x for x in overdue if x["reaccreditation_progress"] == "Re-accreditation in progress"]
    overdue_no_activity = [x for x in overdue if x["reaccreditation_progress"] != "Re-accreditation in progress"]
    action_list = [
        x for x in enriched
        if x["issue_code"] != "REACCREDITATION_OVERDUE"
        and x["issue_code"] not in KNOWN_NONACTIONABLE
    ]

    master_diff = data_row_count(run_dir / "verification_master_differences.csv")
    run_diff = data_row_count(run_dir / "verification_run_differences.csv")
    p75_manual = data_row_count(run_dir / "project75_metadata_actions_MANUAL.csv")
    p79_manual = data_row_count(run_dir / "project79_choice_additions_MANUAL.csv")

    run_stamp = run_dir.name.removeprefix("run_")
    try:
        run_time = datetime.strptime(run_stamp, "%Y%m%d_%H%M%S").replace(tzinfo=TZ)
        run_time_text = run_time.strftime("%d %B %Y, %H:%M EAT")
    except ValueError:
        run_time_text = run_stamp

    catalogue_count = parse_catalogue_count(Path(args.catalogue))
    status = "VERIFIED SUCCESS" if master_diff == 0 and run_diff == 0 and by_severity["ERROR"] == 0 else "REVIEW REQUIRED"

    summary = {
        "schema_version": 1,
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "source_run": run_stamp,
        "source_run_time_eat": run_time_text,
        "verified_archive": str(verified_dir) if verified_dir else "",
        "automation_status": status,
        "public_catalogue_courses": catalogue_count,
        "qc_errors": by_severity["ERROR"],
        "qc_warnings": by_severity["WARNING"],
        "qc_info": by_severity["INFO"],
        "reaccreditation_overdue": by_issue[("WARNING", "REACCREDITATION_OVERDUE")],
        "reaccreditation_overdue_in_progress": len(overdue_in_progress),
        "reaccreditation_overdue_no_new_submission": len(overdue_no_activity),
        "reaccreditation_due_soon": by_issue[("INFO", "REACCREDITATION_DUE_SOON")],
        "review_date_without_reviewer": by_issue[("WARNING", "REVIEW_DATE_WITHOUT_REVIEWER")],
        "run_without_completed_accreditation_warning": by_issue[("WARNING", "RUN_WITHOUT_COMPLETED_ACCREDITATION")],
        "known_1900_exceptions": by_issue[("INFO", "KNOWN_PENDING_ACCREDITATION_1900")],
        "last_run_date_regression": by_issue[("WARNING", "LAST_RUN_DATE_REGRESSION")],
        "p75_manual_metadata_actions": p75_manual,
        "p79_manual_choice_additions": p79_manual,
        "verification_master_differences": master_diff,
        "verification_run_differences": run_diff,
        "action_list_rows": len(action_list),
        "overdue_rows": len(overdue),
    }

    (out_dir / "management_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    md = [
        "# DCEPD Short Course Registry - Management Summary",
        "",
        f"- **Verified run:** {run_time_text}",
        f"- **Automation status:** {status}",
        f"- **Public catalogue:** {catalogue_count if catalogue_count is not None else 'Unknown'} courses",
        f"- **QC errors:** {by_severity['ERROR']}",
        f"- **QC warnings:** {by_severity['WARNING']}",
        f"- **QC information items:** {by_severity['INFO']}",
        f"- **Reaccreditation overdue:** {summary['reaccreditation_overdue']}",
        f"  - with newer re-accreditation submission: {summary['reaccreditation_overdue_in_progress']}",
        f"  - no newer re-accreditation submission recorded: {summary['reaccreditation_overdue_no_new_submission']}",
        f"- **Reaccreditation due soon:** {summary['reaccreditation_due_soon']}",
        f"- **P75 manual metadata actions:** {p75_manual}",
        f"- **P79 manual choice additions:** {p79_manual}",
        "",
        "## Management interpretation",
        "",
        ("No QC errors or verification differences were detected." if status == "VERIFIED SUCCESS" else "The latest run needs technical review before routine management reporting."),
        "Technical GitHub/R/REDCap failures are handled separately and are not part of the routine management report.",
    ]
    (out_dir / "management_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    fields = [
        "record_id", "course_code", "course_name", "severity", "issue_code", "detail",
        "accreditation_date", "date_submitted", "review_sent_date", "approval_date",
        "reaccreditation_progress", "last_date_conducted", "interested_applicants", "public_catalogue",
    ]
    write_csv(out_dir / "action_list.csv", action_list, fields)
    write_csv(out_dir / "overdue_reaccreditation.csv", overdue, fields)

    print(f"Management packet created at {out_dir}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
