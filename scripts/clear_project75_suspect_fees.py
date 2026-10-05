#!/usr/bin/env python3
"""One-time, fail-closed cleanup of suspect Project 75 fee placeholders."""
import argparse, csv, json, os, sys
from pathlib import Path
import requests

API_URL = "https://utafiti.muhas.ac.tz/api/"
FIELD = "fee_per_person_tsh"
LOW, HIGH = 380000, 450000
OUT = Path(".fee-clear-output")
MANIFEST = Path("automation/project75_suspect_fee_clear_2026-10-05.csv")

def api(token, payload):
    r = requests.post(API_URL, data={"token": token, "format": "json", "returnFormat": "json", **payload}, timeout=180)
    r.raise_for_status()
    try:
        return r.json()
    except Exception:
        raise RuntimeError("REDCap returned a non-JSON response") from None

def load_ids():
    with MANIFEST.open(encoding="utf-8-sig", newline="") as f:
        ids = [r["record_id"].strip() for r in csv.DictReader(f) if r["record_id"].strip()]
    if len(ids) != 142 or len(set(ids)) != 142:
        raise RuntimeError(f"Manifest must contain exactly 142 unique record IDs; found {len(ids)} rows / {len(set(ids))} unique.")
    return ids

def export(token, ids):
    payload = {"content":"record","action":"export","type":"flat","rawOrLabel":"raw",
               "rawOrLabelHeaders":"raw","exportSurveyFields":"false","exportDataAccessGroups":"false",
               "fields[0]":"record_id","fields[1]":FIELD}
    for i, rid in enumerate(ids):
        payload[f"records[{i}]"] = rid
    rows = api(token, payload)
    return {str(r["record_id"]): str(r.get(FIELD,"")).strip() for r in rows
            if not str(r.get("redcap_repeat_instrument","")).strip()}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()
    token = os.environ.get("REDCAP_PROJECT75_TOKEN","").strip()
    if not token:
        raise RuntimeError("REDCAP_PROJECT75_TOKEN is not configured.")
    ids = load_ids()
    before = export(token, ids)
    missing = [rid for rid in ids if rid not in before]
    if missing:
        raise RuntimeError(f"Preflight failed: missing record IDs: {missing}")
    eligible, skipped = [], []
    for rid in ids:
        raw = before[rid].replace(",","").strip()
        try:
            value = float(raw)
        except Exception:
            skipped.append({"record_id":rid,"before":before[rid],"reason":"not numeric"})
            continue
        if LOW <= value <= HIGH:
            eligible.append(rid)
        else:
            skipped.append({"record_id":rid,"before":before[rid],"reason":"outside approved suspect band"})
    OUT.mkdir(exist_ok=True)
    (OUT/"preflight.json").write_text(json.dumps({"manifest_count":len(ids),"eligible_count":len(eligible),"skipped":skipped},indent=2))
    print(json.dumps({"manifest_count":len(ids),"eligible_count":len(eligible),"skipped_count":len(skipped),"execute":args.execute}))
    if not args.execute:
        return
    if not eligible:
        raise RuntimeError("Nothing eligible to clear.")
    records = [{"record_id":rid, FIELD:""} for rid in eligible]
    result = api(token, {"content":"record","action":"import","type":"flat","overwriteBehavior":"overwrite",
                         "forceAutoNumber":"false","returnContent":"count","data":json.dumps(records)})
    after = export(token, eligible)
    failed = [{"record_id":rid,"after":after.get(rid)} for rid in eligible if after.get(rid,"").strip()]
    audit = [{"record_id":rid,"before":before[rid],"after":after.get(rid,"")} for rid in eligible]
    with (OUT/"audit.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["record_id","before","after"]); w.writeheader(); w.writerows(audit)
    (OUT/"result.json").write_text(json.dumps({"api_result":result,"cleared_count":len(eligible),"verification_failures":failed},indent=2))
    if failed:
        raise RuntimeError(f"Post-write verification failed for {len(failed)} record(s).")
    print(f"Verified blank fee field for {len(eligible)} record(s).")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
