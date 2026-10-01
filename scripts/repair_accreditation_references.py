#!/usr/bin/env python3
import csv, json, os, re
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo
import requests

REDCAP_URL=os.getenv("REDCAP_URL","https://utafiti.muhas.ac.tz/api/")
TOKEN=os.getenv("REDCAP_PROJECT75_TOKEN","")
ADMIN="accreditation_publication_control"
TZ=ZoneInfo("Africa/Dar_es_Salaam")
OUT=Path(".project75-runtime/accreditation")
DEFAULT_STEM="KB 328/364/"
DEFAULT_VOLUME="25"

def api(data):
    if not TOKEN:
        raise RuntimeError("REDCAP_PROJECT75_TOKEN missing")
    r=requests.post(REDCAP_URL,data={"token":TOKEN,**data},timeout=90)
    r.raise_for_status()
    return r

def export_records():
    return api({"content":"record","format":"json","type":"flat","rawOrLabel":"raw","rawOrLabelHeaders":"raw","returnFormat":"json"}).json()

def import_rows(rows):
    if not rows:
        return
    api({"content":"record","format":"json","type":"flat","overwriteBehavior":"normal","forceAutoNumber":"false","data":json.dumps(rows,separators=(",",":")),"returnContent":"count","returnFormat":"json"})

def pdate(x):
    try:
        return datetime.strptime((x or "").strip(),"%Y-%m-%d").date()
    except Exception:
        return None

def record_id_num(r):
    try:
        return int(r.get("record_id") or 10**9)
    except Exception:
        return 10**9

def main():
    rows=export_records()
    masters=[r for r in rows if not (r.get("redcap_repeat_instrument") or "").strip()]
    admins=[r for r in rows if r.get("record_id")=="1" and r.get("redcap_repeat_instrument")==ADMIN]
    settings=sorted([r for r in admins if r.get("apc_action_type")=="1"],key=lambda r:int(r.get("redcap_repeat_instance") or 0))
    stem=((settings[-1].get("apc_reference_stem") if settings else "") or DEFAULT_STEM).strip()
    vol=((settings[-1].get("apc_reference_volume") if settings else "") or DEFAULT_VOLUME).strip()

    pat=re.compile(r"^"+re.escape(stem)+re.escape(vol)+r"/([0-9]+)$")
    by_serial={}
    max_serial=0
    for r in masters:
        m=pat.match((r.get("approval_reference") or "").strip())
        if not m:
            continue
        n=int(m.group(1))
        max_serial=max(max_serial,n)
        by_serial.setdefault(n,[]).append(r)

    writes=[]
    audit=[]
    for serial,holders in sorted(by_serial.items()):
        if len(holders)<=1:
            continue
        holders=sorted(
            holders,
            key=lambda r:(
                pdate(r.get("accreditation_date")) or date.max,
                pdate(r.get("approval_date")) or date.max,
                record_id_num(r),
            ),
        )
        canonical=holders[0]
        for extra in holders[1:]:
            max_serial+=1
            old=(extra.get("approval_reference") or "").strip()
            new=f"{stem}{vol}/{max_serial:03d}"
            writes.append({"record_id":extra["record_id"],"approval_reference":new})
            audit.append({
                "record_id":extra["record_id"],
                "canonical_record_id":canonical["record_id"],
                "old_reference":old,
                "new_reference":new,
                "accreditation_date":extra.get("accreditation_date",""),
                "approval_date":extra.get("approval_date",""),
                "repair_timestamp":datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"),
            })

    if not writes:
        print("reference_repairs=0")
        return

    import_rows(writes)

    refreshed=[r for r in export_records() if not (r.get("redcap_repeat_instrument") or "").strip()]
    lookup={r["record_id"]:r for r in refreshed}
    bad=[x["record_id"] for x in audit if lookup.get(x["record_id"],{}).get("approval_reference")!=x["new_reference"]]
    if bad:
        raise RuntimeError("Reference repair verification failed for records: "+",".join(bad))

    seen={}
    for r in refreshed:
        m=pat.match((r.get("approval_reference") or "").strip())
        if m:
            seen.setdefault(int(m.group(1)),[]).append(r["record_id"])
    remaining={k:v for k,v in seen.items() if len(v)>1}
    if remaining:
        raise RuntimeError("Duplicate serials remain after repair: "+json.dumps(remaining))

    OUT.mkdir(parents=True,exist_ok=True)
    path=OUT/"reference_repairs.csv"
    with path.open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=list(audit[0]))
        w.writeheader()
        w.writerows(audit)

    print(f"reference_repairs={len(audit)}")
    print(f"audit_file={path}")

if __name__=="__main__":
    main()
