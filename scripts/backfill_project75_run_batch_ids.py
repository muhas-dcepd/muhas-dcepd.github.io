#!/usr/bin/env python3
"""Safely backfill/verify Project 75 Course Run Log run_batch_id.

Writes only one derived record field:
  run_batch_id = <record_id>-<redcap_repeat_instance>

No metadata/data-dictionary writes are performed.
"""
import json, os, sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API=os.getenv("REDCAP_API_URL","https://utafiti.muhas.ac.tz/api/")
TOKEN=os.getenv("REDCAP_PROJECT75_TOKEN","")


def post(content, extra=None):
    if not TOKEN:
        raise RuntimeError("REDCAP_PROJECT75_TOKEN is missing")
    body=dict(token=TOKEN,content=content,format="json",returnFormat="json")
    body.update(extra or {})
    with urlopen(Request(API,data=urlencode(body).encode()),timeout=120) as r:
        return json.load(r)


def export_rows():
    fields=["record_id","run_batch_id"]
    params={
        "action":"export","type":"flat","rawOrLabel":"raw",
        "rawOrLabelHeaders":"raw","exportSurveyFields":"false",
        "exportDataAccessGroups":"false",
    }
    for i,v in enumerate(fields):
        params[f"fields[{i}]"]=v
    rows=post("record",params)
    if not isinstance(rows,list):
        raise RuntimeError("Unexpected Project 75 export response")
    return rows


def target_rows(rows):
    out=[]
    seen=set()
    for r in rows:
        if str(r.get("redcap_repeat_instrument","")).strip()!="course_run_log":
            continue
        rid=str(r.get("record_id","")).strip()
        inst=str(r.get("redcap_repeat_instance","")).strip()
        if not rid or not inst:
            raise RuntimeError("Course Run Log row has incomplete repeat key")
        key=(rid,inst)
        if key in seen:
            raise RuntimeError(f"Duplicate Course Run Log repeat key: {rid}-{inst}")
        seen.add(key)
        expected=f"{rid}-{inst}"
        current=str(r.get("run_batch_id","")).strip()
        if current and current!=expected:
            raise RuntimeError(
                f"Existing run_batch_id mismatch for {rid}-{inst}: {current!r} != {expected!r}"
            )
        if not current:
            out.append({
                "record_id":rid,
                "redcap_repeat_instrument":"course_run_log",
                "redcap_repeat_instance":inst,
                "run_batch_id":expected,
            })
    return out, len(seen)


def import_rows(rows):
    if not rows:
        return
    result=post("record",{
        "action":"import","type":"flat","overwriteBehavior":"normal",
        "forceAutoNumber":"false",
        "data":json.dumps(rows,separators=(",",":")),
        "returnContent":"count","returnFormat":"json",
    })
    print("import_result="+json.dumps(result,separators=(",",":")))


def main():
    before=export_rows()
    updates,total=target_rows(before)
    print(f"course_run_log_rows={total}")
    print(f"missing_run_batch_id={len(updates)}")
    if updates:
        print("planned_ids="+",".join(x["run_batch_id"] for x in updates))
        import_rows(updates)

    after=export_rows()
    remaining,total_after=target_rows(after)
    if total_after!=total:
        raise RuntimeError(
            f"Course Run Log row count changed during verification: {total} -> {total_after}"
        )
    if remaining:
        raise RuntimeError(
            "run_batch_id verification failed; still missing: "+
            ",".join(x["run_batch_id"] for x in remaining)
        )
    print(f"verified_run_batch_ids={total_after}")
    print("run_batch_id_backfill_status=success")


if __name__=="__main__":
    try:
        main()
    except Exception as exc:
        print(f"run_batch_id_backfill_status=failure;reason={exc}",file=sys.stderr)
        raise
